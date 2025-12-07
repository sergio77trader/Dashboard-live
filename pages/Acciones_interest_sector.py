import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import re

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Options Screener Pro")

# --- BASE DE DATOS ---
CEDEAR_SET = {
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AMD', 'INTC', 'QCOM',
    'KO', 'PEP', 'WMT', 'PG', 'COST', 'MCD', 'SBUX', 'DIS', 'NKE',
    'XOM', 'CVX', 'SLB', 'PBR', 'VIST',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'V', 'MA', 'BRK-B',
    'GGAL', 'BMA', 'YPF', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'GLOB', 'MELI', 'BIOX'
}

STOCK_GROUPS = {
    '🇦🇷 Argentina (ADRs en USA)': ['GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX'],
    '🇺🇸 Big Tech (Magnificent 7)': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META'],
    '🇺🇸 High Volatility & AI': ['AMD', 'PLTR', 'COIN', 'MSTR', 'ARM', 'SMCI', 'TSM', 'AVGO'],
    '🇺🇸 Blue Chips (Dow Jones)': ['KO', 'MCD', 'JPM', 'DIS', 'BA', 'CAT', 'XOM', 'CVX', 'WMT']
}

# --- FUNCIONES AUXILIARES ---
def get_sentiment_label(ratio):
    if ratio < 0.7: return "🚀 ALCISTA"
    elif ratio > 1.0: return "🐻 BAJISTA"
    else: return "⚖️ NEUTRAL"

def generate_links(ticker, has_cedear):
    yahoo_link = f"https://finance.yahoo.com/quote/{ticker}/options"
    # Si es argentino, el gráfico local suele ser BCBA:GGAL, si es cedear BCBA:AAPL
    symbol = f"BCBA%3A{ticker}" if has_cedear else ticker
    tv_link = f"https://es.tradingview.com/chart/?symbol={symbol}"
    return yahoo_link, tv_link

# --- MOTOR DE ANÁLISIS BLINDADO (V2.0) ---
@st.cache_data(ttl=900) # Cache 15 min
def analyze_options_chain(ticker):
    try:
        tk = yf.Ticker(ticker)
        
        # --- FIX ROBUSTEZ PRECIO ---
        # Intentamos 3 métodos para conseguir el precio actual del ADR
        current_price = 0.0
        
        # Método 1: Fast Info (Más rápido y preciso para tiempo real)
        try:
            if hasattr(tk, 'fast_info') and tk.fast_info.last_price:
                current_price = float(tk.fast_info.last_price)
        except: pass
        
        # Método 2: Historial 1 día (Fallback clásico)
        if current_price == 0:
            hist = tk.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                
        # Método 3: Historial 5 días (Fallback extremo para fines de semana o iliquidez)
        if current_price == 0:
            hist_wk = tk.history(period="5d")
            if not hist_wk.empty:
                current_price = hist_wk['Close'].iloc[-1]
        
        # Si después de todo sigue siendo 0, abortamos ese ticker
        if current_price == 0: 
            return None

        # --- EXTRACCIÓN DE OPCIONES ---
        try:
            exps = tk.options
        except:
            return None # Error de conexión con Yahoo Options
            
        if not exps: return None # No tiene opciones listadas
        
        # Tomamos el vencimiento más cercano
        target_date = exps[0]
        try:
            opts = tk.option_chain(target_date)
            calls = opts.calls
            puts = opts.puts
        except:
            return None # Fallo al descargar la cadena
        
        # Validación de datos vacíos
        if calls.empty and puts.empty: return None

        total_call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
        total_put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 0
        
        # Evitar división por cero
        if total_call_oi == 0: total_call_oi = 1 
        
        pc_ratio = total_put_oi / total_call_oi
        
        # Cálculo de Max Pain
        # Unimos strikes de calls y puts
        strikes = sorted(list(set(calls['strike'].tolist() + puts['strike'].tolist())))
        # Filtramos strikes muy lejanos (ruido)
        strikes = [s for s in strikes if current_price * 0.6 < s < current_price * 1.4]
        
        cash_values = []
        for strike in strikes:
            # Cuánto dinero pierden los compradores de calls si cierra en este strike
            intrinsic_calls = calls.apply(lambda row: max(0, strike - row['strike']) * row.get('openInterest', 0), axis=1).sum()
            # Cuánto dinero pierden los compradores de puts
            intrinsic_puts = puts.apply(lambda row: max(0, row['strike'] - strike) * row.get('openInterest', 0), axis=1).sum()
            cash_values.append(intrinsic_calls + intrinsic_puts)
        
        max_pain = strikes[np.argmin(cash_values)] if cash_values else current_price
        
        return {
            'Ticker': ticker, 
            'Price': current_price, 
            'Max_Pain': max_pain,
            'PC_Ratio': pc_ratio, 
            'Call_OI': total_call_oi, 
            'Put_OI': total_put_oi,
            'Expiration': target_date, 
            'Has_Cedear': ticker in CEDEAR_SET,
            'Calls_DF': calls, 
            'Puts_DF': puts
        }
    except Exception as e:
        # print(f"Error en {ticker}: {e}") # Solo para debug local
        return None

def get_batch_analysis(ticker_list):
    results = []
    prog = st.progress(0, text="Iniciando escaneo...")
    total = len(ticker_list)
    
    for i, t in enumerate(ticker_list):
        data = analyze_options_chain(t)
        if data: 
            results.append(data)
        prog.progress((i + 1) / total, text=f"Analizando {t}...")
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🔮 SystemaTrader: Radar de Sentimiento Pro")

if 'analysis_results' not in st.session_state:
    st.session_state['analysis_results'] = {}
    st.session_state['current_view'] = "Esperando..."

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Modo Grupal")
    selected_group = st.selectbox("Seleccionar Grupo:", list(STOCK_GROUPS.keys()))
    
    if st.button("🔍 Escanear Grupo", type="primary"):
        tickers = STOCK_GROUPS[selected_group]
        st.session_state['current_view'] = selected_group
        with st.spinner(f"Analizando {len(tickers)} activos..."):
            st.session_state['analysis_results'] = get_batch_analysis(tickers)

    st.divider()
    
    st.header("2. Tu Lista Personal")
    st.info("Escribe los activos (Ej: GGAL, YPF, MELI)")
    custom_list_raw = st.text_area("Tickers:", height=100)
    
    if st.button("🚀 Analizar Lista"):
        if custom_list_raw:
            custom_tickers = [t.strip().upper() for t in re.split(r'[,\s]+', custom_list_raw) if t.strip()]
            if custom_tickers:
                st.session_state['current_view'] = "Lista Personalizada"
                with st.spinner(f"Analizando {len(custom_tickers)} activos..."):
                    st.session_state['analysis_results'] = get_batch_analysis(custom_tickers)
            else:
                st.error("Lista vacía.")

# --- DASHBOARD ---
st.subheader(f"1️⃣ Tablero: {st.session_state.get('current_view', 'Sin Datos')}")

if st.session_state['analysis_results']:
    results = st.session_state['analysis_results']
    df_table = pd.DataFrame(results)
    
    if not df_table.empty:
        df_display = df_table.copy()
        df_display['Sentimiento'] = df_display['PC_Ratio'].apply(get_sentiment_label)
        
        st.dataframe(
            df_display[['Ticker', 'Price', 'Max_Pain', 'PC_Ratio', 'Sentimiento', 'Has_Cedear']],
            column_config={
                "Ticker": "Activo", 
                "Price": st.column_config.NumberColumn("Precio ADR", format="$%.2f"),
                "Max_Pain": st.column_config.NumberColumn("Max Pain", format="$%.2f"),
                "PC_Ratio": st.column_config.NumberColumn("Put/Call Ratio", format="%.2f"),
                "Has_Cedear": st.column_config.CheckboxColumn("Es Argentino/Cedear?", default=False)
            },
            use_container_width=True, hide_index=True
        )
    else: 
        st.warning("⚠️ No se encontraron datos de opciones.")
        st.info("Posible causa: Los ADRs argentinos tienen poca liquidez de opciones en USA y Yahoo Finance no reporta datos si no hay operaciones recientes.")

    # --- ANÁLISIS DETALLADO ---
    st.divider()
    st.subheader("2️⃣ Análisis Profundo")
    
    ticker_options = [r['Ticker'] for r in results]
    if ticker_options:
        selected_ticker = st.selectbox("Selecciona Activo para ver Muros:", ticker_options)
        asset_data = next((i for i in results if i["Ticker"] == selected_ticker), None)
        
        if asset_data:
            link_yahoo, link_tv = generate_links(selected_ticker, asset_data['Has_Cedear'])
            
            # Encabezado con Links
            col_links1, col_links2 = st.columns(2)
            col_links1.markdown(f"[🔍 Auditar en Yahoo Finance]({link_yahoo})")
            col_links2.markdown(f"[📈 Gráfico TradingView]({link_tv})")

            # Métricas
            k1, k2, k3, k4 = st.columns(4)
            delta_pain = asset_data['Max_Pain'] - asset_data['Price']
            k1.metric("Precio ADR", f"${asset_data['Price']:.2f}")
            k2.metric("Max Pain", f"${asset_data['Max_Pain']:.2f}", delta=f"{delta_pain:.2f}", delta_color="off", help="El precio donde los creadores de mercado ganan más dinero.")
            k3.metric("Sentimiento", get_sentiment_label(asset_data['PC_Ratio']), delta=f"Ratio: {asset_data['PC_Ratio']:.2f}")
            k4.metric("Vencimiento", str(asset_data['Expiration']))

            # Gráficos
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.markdown("**Sentimiento (Open Interest)**")
                labels = ['Calls (Toros)', 'Puts (Osos)']
                values = [asset_data['Call_OI'], asset_data['Put_OI']]
                fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker=dict(colors=['#00CC96', '#EF553B']))])
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with c2:
                st.markdown("**Muros de Liquidez (Gamma Exposure)**")
                calls, puts = asset_data['Calls_DF'], asset_data['Puts_DF']
                price = asset_data['Price']
                # Filtro visual para no ver strikes locos
                min_s, max_s = price * 0.80, price * 1.20
                c_filt = calls[(calls['strike'] >= min_s) & (calls['strike'] <= max_s)]
                p_filt = puts[(puts['strike'] >= min_s) & (puts['strike'] <= max_s)]
                
                fig_wall = go.Figure()
                fig_wall.add_trace(go.Bar(x=c_filt['strike'], y=c_filt['openInterest'], name='Calls (Resistencia)', marker_color='#00CC96'))
                fig_wall.add_trace(go.Bar(x=p_filt['strike'], y=p_filt['openInterest'], name='Puts (Soporte)', marker_color='#EF553B'))
                fig_wall.add_vline(x=price, line_dash="dash", line_color="white", annotation_text="Precio Actual")
                fig_wall.add_vline(x=asset_data['Max_Pain'], line_dash="dash", line_color="yellow", annotation_text="Max Pain")
                fig_wall.update_layout(barmode='overlay', height=350, margin=dict(t=20), xaxis_title="Strike ($USD)")
                st.plotly_chart(fig_wall, use_container_width=True)

else:
    st.info("👈 Selecciona un grupo en el menú lateral para comenzar.")
