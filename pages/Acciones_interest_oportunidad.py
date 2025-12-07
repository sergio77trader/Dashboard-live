import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import re
import time
import requests # Necesario para evitar bloqueo inmediato

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Options Screener Ultimate")

# --- BASE DE DATOS MAESTRA ---
CEDEAR_DATABASE = {
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'XLE', 'XLF', 'ARKK', 'EWZ', 'GLD', 'SLV',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AMD', 'NFLX', 'INTC', 'QCOM', 'AVGO', 'CRM', 'CSCO', 'ORCL', 'IBM', 'UBER', 'ABNB', 'PLTR', 'SPOT', 'TSM', 'MU', 'ARM', 'SMCI',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'PG', 'JNJ', 'PFE', 'MRK', 'LLY', 'XOM', 'CVX', 'SLB', 'BA', 'CAT', 'MMM', 'GE', 'DE', 'F', 'GM', 'TM',
    'COIN', 'MSTR', 'HUT', 'BITF',
    'PBR', 'VALE', 'ITUB', 'BBD', 'BABA', 'JD', 'BIDU'
}

STOCK_GROUPS = {
    '🇦🇷 Argentina (ADRs)': ['GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI'],
    '🇺🇸 ETFs (Índices)': ['SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'XLE', 'XLF', 'ARKK', 'EWZ'],
    '🇺🇸 Magnificent 7 + Tech': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX', 'CRM'],
    '🇺🇸 Semiconductores & AI': ['AMD', 'INTC', 'QCOM', 'AVGO', 'TSM', 'MU', 'ARM', 'SMCI', 'PLTR'],
    '🇺🇸 Financiero': ['JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'BRK-B', 'PYPL'],
    '🇺🇸 Consumo & Dividendos': ['KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'PG', 'JNJ', 'XOM', 'CVX'],
    '🇺🇸 Crypto & Volatilidad': ['COIN', 'MSTR', 'UBER', 'ABNB', 'SQ', 'TSLA'],
    '🌎 Brasil & China': ['PBR', 'VALE', 'ITUB', 'BABA', 'JD', 'BIDU']
}

# --- FUNCIONES ---
def get_sentiment_label(ratio):
    if ratio < 0.7: return "🚀 ALCISTA"
    elif ratio > 1.0: return "🐻 BAJISTA"
    else: return "⚖️ NEUTRAL"

def generate_links(ticker):
    yahoo_link = f"https://finance.yahoo.com/quote/{ticker}/options"
    tv_link = f"https://es.tradingview.com/chart/?symbol=BCBA%3A{ticker}"
    return yahoo_link, tv_link

def check_proximity(price, wall_price, threshold_pct):
    if wall_price == 0 or price == 0: return False
    distance = abs(price - wall_price) / price * 100
    return distance <= threshold_pct

# --- PROTOCOLO ANTI-BLOQUEO ---
def get_fake_session():
    """Genera una sesión que simula ser Chrome para que Yahoo no bloquee la IP de Streamlit Cloud"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

@st.cache_data(ttl=900)
def analyze_options_chain(ticker):
    try:
        # Usamos sesión fake para evitar error 403/429
        session = get_fake_session()
        tk = yf.Ticker(ticker, session=session)
        
        current_price = 0
        try:
            if hasattr(tk, 'fast_info') and tk.fast_info.last_price:
                current_price = float(tk.fast_info.last_price)
        except: pass
        
        if current_price == 0:
            try:
                hist = tk.history(period="5d")
                if not hist.empty: current_price = hist['Close'].iloc[-1]
            except: pass
        
        if current_price == 0: return None

        try:
            exps = tk.options
        except: return None
            
        if not exps: return None
        
        target_date = None
        calls, puts = pd.DataFrame(), pd.DataFrame()
        
        # Miramos hasta 2 vencimientos (Estrategia rápida)
        for date in exps[:2]:
            try:
                opts = tk.option_chain(date)
                c, p = opts.calls, opts.puts
                if not c.empty or not p.empty:
                    calls, puts = c, p
                    target_date = date
                    break
            except: continue
        
        if target_date is None: return None
        
        total_call_oi = calls['openInterest'].sum()
        total_put_oi = puts['openInterest'].sum()
        if total_call_oi == 0: total_call_oi = 1
        
        pc_ratio = total_put_oi / total_call_oi
        
        call_wall = calls.loc[calls['openInterest'].idxmax()]['strike'] if not calls.empty else 0
        put_wall = puts.loc[puts['openInterest'].idxmax()]['strike'] if not puts.empty else 0
        
        data_quality = "OK"
        market_consensus = (call_wall + put_wall) / 2
        calculation_price = current_price
        if market_consensus > 0:
            if abs(current_price - market_consensus) / market_consensus > 0.6:
                data_quality = "ERROR_PRECIO"

        strikes = sorted(list(set(calls['strike'].tolist() + puts['strike'].tolist())))
        strikes = [s for s in strikes if calculation_price * 0.5 < s < calculation_price * 1.5]
        
        cash_values = []
        for strike in strikes:
            intrinsic_calls = calls.apply(lambda row: max(0, strike - row['strike']) * row.get('openInterest', 0), axis=1).sum()
            intrinsic_puts = puts.apply(lambda row: max(0, row['strike'] - strike) * row.get('openInterest', 0), axis=1).sum()
            cash_values.append(intrinsic_calls + intrinsic_puts)
        
        max_pain = strikes[np.argmin(cash_values)] if cash_values else calculation_price
        
        return {
            'Ticker': ticker, 'Price': current_price, 'Max_Pain': max_pain,
            'PC_Ratio': pc_ratio, 'Call_OI': total_call_oi, 'Put_OI': total_put_oi,
            'Expiration': target_date,
            'Call_Wall': call_wall, 'Put_Wall': put_wall,
            'Data_Quality': data_quality, 'Calculated_Price_Ref': calculation_price,
            'Calls_DF': calls, 'Puts_DF': puts
        }
    except Exception: return None

def get_batch_analysis(ticker_list):
    results = []
    prog = st.progress(0, text="Analizando lote...")
    total = len(ticker_list)
    
    for i, t in enumerate(ticker_list):
        data = analyze_options_chain(t)
        if data: results.append(data)
        
        # Pequeña pausa táctica dentro del lote
        time.sleep(0.1)
        prog.progress((i + 1) / total)
        
    prog.empty()
    return results

# --- GESTIÓN DE ESTADO (MEMORIA DE RESULTADOS) ---
if 'master_results' not in st.session_state:
    st.session_state['master_results'] = [] # Aquí se guardarán todos los activos acumulados

# --- INTERFAZ ---
st.title("🌎 SystemaTrader: Escáner de Opciones (Modo Lotes)")

# --- SIDEBAR: MOTOR DE LOTES ---
with st.sidebar:
    st.header("⚙️ Configuración")
    proximity_threshold = st.slider("Alerta Proximidad (%)", 1, 10, 3)
    
    st.divider()
    st.header("🔬 Escaneo por Lotes (15)")
    st.info("Estrategia para evitar bloqueos: Escanea un lote, espera unos segundos, y escanea el siguiente. Los resultados se suman.")
    
    # 1. Preparar Lotes de 15
    all_tickers = sorted(list(CEDEAR_DATABASE))
    BATCH_SIZE = 15
    batches = [all_tickers[i:i + BATCH_SIZE] for i in range(0, len(all_tickers), BATCH_SIZE)]
    
    # 2. Selector de Lote
    batch_options = [f"Lote {i+1}: {b[0]}...{b[-1]}" for i, b in enumerate(batches)]
    selected_batch_idx = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_options[x])
    
    # 3. Botón de Acción
    if st.button("🚀 ESCANEAR Y ACUMULAR", type="primary"):
        target_tickers = batches[selected_batch_idx]
        with st.spinner(f"Procesando {len(target_tickers)} activos..."):
            new_data = get_batch_analysis(target_tickers)
            
            # Lógica de Acumulación (Evitar duplicados)
            existing_tickers = {item['Ticker'] for item in st.session_state['master_results']}
            added_count = 0
            for item in new_data:
                if item['Ticker'] not in existing_tickers:
                    st.session_state['master_results'].append(item)
                    added_count += 1
            
            if added_count > 0:
                st.success(f"✅ Agregados {added_count} activos nuevos.")
            else:
                st.warning("⚠️ No se encontraron datos nuevos o Yahoo bloqueó este lote.")

    # 4. Métricas de Progreso
    total_found = len(st.session_state['master_results'])
    total_db = len(CEDEAR_DATABASE)
    st.metric("Total Acumulado", f"{total_found} / {total_db}")
    st.progress(total_found / total_db if total_db > 0 else 0)

    if st.button("🗑️ Borrar Todo y Empezar"):
        st.session_state['master_results'] = []
        st.rerun()

    st.markdown("---")
    
    # Opcional: Escaneo Manual
    with st.expander("Escaneo Manual Rápido"):
        custom_input = st.text_area("Tickers:", height=60)
        if st.button("Analizar Manual"):
            if custom_input:
                custom_tickers = [t.strip().upper() for t in re.split(r'[,\s]+', custom_input) if t.strip()]
                new_manual = get_batch_analysis(custom_tickers)
                # Acumular manual también
                existing = {item['Ticker'] for item in st.session_state['master_results']}
                for item in new_manual:
                    if item['Ticker'] not in existing:
                        st.session_state['master_results'].append(item)
                st.rerun()

# --- TABLERO DE RESULTADOS ---
st.subheader(f"📊 Resultados Consolidados ({len(st.session_state['master_results'])} Activos)")

if st.session_state['master_results']:
    results = st.session_state['master_results']
    df_table = pd.DataFrame(results)
    
    # --- PROCESAMIENTO VISUAL ---
    def get_alert_status(row):
        if row['Data_Quality'] == 'ERROR_PRECIO': return "❌ ERROR DATA"
        status = []
        if check_proximity(row['Price'], row['Call_Wall'], proximity_threshold): status.append("🧱 TECHO")
        if check_proximity(row['Price'], row['Put_Wall'], proximity_threshold): status.append("🟢 PISO")
        return " + ".join(status) if status else "OK"

    df_display = df_table.copy()
    df_display['Alerta'] = df_display.apply(get_alert_status, axis=1)
    df_display['Sentimiento'] = df_display['PC_Ratio'].apply(get_sentiment_label)
    
    # Cálculos %
    df_display['% Techo'] = ((df_display['Call_Wall'] - df_display['Price']) / df_display['Price']) * 100
    df_display['% Piso'] = ((df_display['Put_Wall'] - df_display['Price']) / df_display['Price']) * 100

    # Filtros
    col_filter1, col_filter2 = st.columns([1, 4])
    with col_filter1:
        show_only_alerts = st.checkbox("🔥 Solo Alertas", value=False)
    
    if show_only_alerts:
        df_final = df_display[df_display['Alerta'] != "OK"]
    else:
        df_final = df_display.sort_values(by=['Alerta', 'Ticker'], ascending=[False, True])

    # Tabla
    st.dataframe(
        df_final[['Ticker', 'Price', 'Max_Pain', 'Alerta', 'Call_Wall', '% Techo', 'Put_Wall', '% Piso', 'Sentimiento']],
        column_config={
            "Ticker": "Activo", 
            "Price": st.column_config.NumberColumn("Precio", format="$%.2f"),
            "Max_Pain": st.column_config.NumberColumn("Max Pain", format="$%.2f"),
            "Alerta": st.column_config.TextColumn("Estado"),
            "Call_Wall": st.column_config.NumberColumn("Techo", format="$%.2f"),
            "% Techo": st.column_config.NumberColumn("Dist. Techo %", format="%.2f%%"),
            "Put_Wall": st.column_config.NumberColumn("Piso", format="$%.2f"),
            "% Piso": st.column_config.NumberColumn("Dist. Piso %", format="%.2f%%"),
        },
        use_container_width=True, hide_index=True, height=600
    )

    # --- DETALLE INDIVIDUAL ---
    st.divider()
    st.subheader("2️⃣ Análisis Profundo")
    ticker_options = sorted([r['Ticker'] for r in results])
    if ticker_options:
        selected_ticker = st.selectbox("Selecciona Activo:", ticker_options)
        asset_data = next((i for i in results if i["Ticker"] == selected_ticker), None)
        
        if asset_data:
            if asset_data['Data_Quality'] == 'ERROR_PRECIO':
                st.error(f"🚨 **ERROR DE PRECIO:** Yahoo reporta ${asset_data['Price']:.2f} pero opciones apunta a ${asset_data['Max_Pain']:.2f}.")

            k1, k2, k3, k4, k5 = st.columns(5)
            
            dist_max_pain = ((asset_data['Max_Pain'] - asset_data['Price']) / asset_data['Price']) * 100
            dist_techo = ((asset_data['Call_Wall'] - asset_data['Price']) / asset_data['Price']) * 100
            dist_piso = ((asset_data['Put_Wall'] - asset_data['Price']) / asset_data['Price']) * 100

            k1.metric("Precio", f"${asset_data['Price']:.2f}")
            k2.metric("Max Pain", f"${asset_data['Max_Pain']:.2f}", delta=f"{dist_max_pain:.1f}%", delta_color="off")
            k3.metric("Sentimiento", get_sentiment_label(asset_data['PC_Ratio']), delta=f"Ratio: {asset_data['PC_Ratio']:.2f}")
            k4.metric("Techo", f"${asset_data['Call_Wall']:.2f}", delta=f"{dist_techo:.1f}%")
            k5.metric("Piso", f"${asset_data['Put_Wall']:.2f}", delta=f"{dist_piso:.1f}%")

            c1, c2 = st.columns([1, 2])
            with c1:
                fig_pie = go.Figure(data=[go.Pie(labels=['Calls', 'Puts'], values=[asset_data['Call_OI'], asset_data['Put_OI']], hole=.4)])
                fig_pie.update_layout(height=250, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with c2:
                # Grafico de Barras
                calls, puts = asset_data['Calls_DF'], asset_data['Puts_DF']
                center_price = asset_data['Calculated_Price_Ref']
                min_s, max_s = center_price * 0.85, center_price * 1.15
                c_filt = calls[(calls['strike'] >= min_s) & (calls['strike'] <= max_s)]
                p_filt = puts[(puts['strike'] >= min_s) & (puts['strike'] <= max_s)]
                
                fig_wall = go.Figure()
                fig_wall.add_trace(go.Bar(x=c_filt['strike'], y=c_filt['openInterest'], name='Calls', marker_color='#00CC96'))
                fig_wall.add_trace(go.Bar(x=p_filt['strike'], y=p_filt['openInterest'], name='Puts', marker_color='#EF553B'))
                fig_wall.add_vline(x=asset_data['Price'], line_dash="dash", line_color="white", annotation_text="Precio")
                fig_wall.add_vline(x=asset_data['Max_Pain'], line_dash="dash", line_color="yellow", annotation_text="Max Pain")
                fig_wall.update_layout(barmode='overlay', height=350, margin=dict(t=20))
                st.plotly_chart(fig_wall, use_container_width=True)

            link_yahoo, link_tv = generate_links(selected_ticker)
            st.markdown(f"🔗 [Yahoo Finance]({link_yahoo}) | [TradingView]({link_tv})")

else:
    st.info("Utiliza el panel izquierdo para escanear lotes y acumular resultados.")
