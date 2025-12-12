import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
import time
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Escáner Pro: HA + ADX", layout="wide")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    .stDataFrame { font-size: 0.9rem; }
    div[data-testid="stMetric"], .metric-card {
        background-color: #0e1117; border: 1px solid #303030;
        padding: 10px; border-radius: 8px; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS EXTENDIDA (CEDEARs & ADRs) ---
TICKERS_DB = sorted([
    # ARGENTINA (ADRs)
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX',
    # USA TECH & GROWTH
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB',
    # SEMICONDUCTORES
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML',
    # FINANCIEROS
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK',
    # CONSUMO & SALUD
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'PG', 'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH',
    # INDUSTRIA & ENERGIA
    'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'F', 'GM', 'TM', 'HMC',
    # CHINA
    'BABA', 'JD', 'BIDU', 'NIO', 'PDD', 'TCEHY', 'TCOM',
    # BRASIL & LATAM
    'PBR', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV',
    # MINERÍA & COMMODITIES
    'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP',
    # ETFS CLAVE
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'ARKK', 'SMH', 'GLD', 'SLV', 'GDX'
])

# --- FUNCIONES DE CÁLCULO (INTACTAS) ---

def calculate_heikin_ashi(df):
    """Calcula Heikin Ashi iterativo"""
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        prev_open = ha_open[-1]
        prev_close = df_ha['HA_Close'].iloc[i-1]
        ha_open.append((prev_open + prev_close) / 2)
        
    df_ha['HA_Open'] = ha_open
    df_ha['HA_High'] = df_ha[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df_ha['HA_Low'] = df_ha[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    
    # 1 Verde, -1 Rojo
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

@st.cache_data(ttl=3600)
def get_data(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def analyze_ticker(ticker, interval, period, adx_len, adx_th):
    """
    Analiza un ticker y devuelve:
    1. La ÚLTIMA señal (para la tabla).
    2. El DF completo (para el gráfico).
    3. TODAS las señales históricas (para el backtesting visual).
    """
    df = get_data(ticker, interval, period)
    if df is None: return None, None, []

    # 1. Calcular ADX
    try:
        df.ta.adx(length=adx_len, append=True)
    except: return None, None, [] # Si falla TA
        
    adx_col = f"ADX_{adx_len}"
    
    # 2. Calcular HA
    df_ha = calculate_heikin_ashi(df)
    
    # 3. Lógica de Señal
    signals = []
    in_position = False
    
    for i in range(1, len(df_ha)):
        date = df_ha.index[i]
        ha_color = df_ha['Color'].iloc[i]
        adx_val = df_ha[adx_col].iloc[i]
        price = df_ha['Close'].iloc[i]
        
        # Compra
        if not in_position and ha_color == 1 and adx_val > adx_th:
            in_position = True
            signals.append({'Fecha': date, 'Tipo': '🟢 COMPRA', 'Precio': price, 'ADX': adx_val})
            
        # Venta
        elif in_position and ha_color == -1:
            in_position = False
            signals.append({'Fecha': date, 'Tipo': '🔴 VENTA', 'Precio': price, 'ADX': adx_val})
    
    last_signal = signals[-1] if signals else None
    
    return last_signal, df_ha, signals

# --- UI LATERAL ---
with st.sidebar:
    st.header("⚙️ Centro de Comando")
    st.info(f"Base de Datos Expandida: {len(TICKERS_DB)} Activos")
    
    interval = st.selectbox("Temporalidad", ["1mo", "1wk", "1d", "1h"], index=0)
    period_map = {"1mo": "max", "1wk": "10y", "1d": "5y", "1h": "730d"}
    
    st.divider()
    st.subheader("Estrategia (ADX + HA)")
    adx_len = st.number_input("Longitud ADX", value=14)
    adx_th = st.number_input("Umbral ADX", value=20)
    
    st.divider()
    st.subheader("1. Escaneo por Lotes")
    
    batch_size = st.slider("Tamaño del Lote", 5, 50, 10)
    batches = [TICKERS_DB[i:i + batch_size] for i in range(0, len(TICKERS_DB), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch_idx = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    scan_btn = st.button("🚀 ESCANEAR LOTE", type="primary")
    
    st.divider()
    st.subheader("2. Lista Personalizada")
    st.caption("Escribe tickers separados por coma o espacio (Ej: AAPL, KO, GGAL).")
    custom_input = st.text_area("Ingresar Activos:", height=70)
    custom_btn = st.button("🔎 ANALIZAR MI LISTA")
    
    st.divider()
    if st.button("🗑️ Borrar Resultados"):
        st.session_state['scan_results'] = []
        st.rerun()

# --- APP PRINCIPAL ---
st.title("🛰️ Escáner Pro: Señales y Backtesting Visual")

if 'scan_results' not in st.session_state:
    st.session_state['scan_results'] = []

# --- FUNCIÓN DE PROCESAMIENTO ---
def process_tickers(ticker_list):
    prog_bar = st.progress(0)
    status_text = st.empty()
    new_results = []
    
    # Filtramos para no re-analizar lo que ya está en tabla en la misma sesión
    existing_tickers = [x['Ticker'] for x in st.session_state['scan_results']]
    to_analyze = [t for t in ticker_list if t not in existing_tickers]
    
    if not to_analyze:
        st.toast("Esos activos ya están en la tabla.", icon="ℹ️")
        prog_bar.empty()
        return

    for i, t in enumerate(to_analyze):
        status_text.text(f"Analizando {t}...")
        # Solo necesitamos la última señal para la tabla
        last_sig, _, _ = analyze_ticker(t, interval, period_map[interval], adx_len, adx_th)
        
        if last_sig:
            last_sig['Ticker'] = t
            new_results.append(last_sig)
            
        prog_bar.progress((i + 1) / len(to_analyze))
        time.sleep(0.1) # Pequeña pausa para no saturar Yahoo
    
    # Acumulación: Agregamos lo nuevo a lo viejo
    st.session_state['scan_results'].extend(new_results)
    
    status_text.empty(); prog_bar.empty()
    if new_results:
        st.success(f"Se agregaron {len(new_results)} activos.")
    else:
        st.warning("No se encontraron señales en los activos seleccionados.")

# --- HANDLERS DE BOTONES ---
if scan_btn:
    targets = batches[sel_batch_idx]
    process_tickers(targets)

if custom_btn and custom_input:
    # Limpieza de input
    raw_tickers = re.split(r'[,\s\n]+', custom_input)
    clean_tickers = [t.upper().strip() for t in raw_tickers if t]
    if clean_tickers:
        process_tickers(clean_tickers)
    else:
        st.error("Lista vacía.")

# --- MOSTRAR RESULTADOS ---
if st.session_state['scan_results']:
    
    df_results = pd.DataFrame(st.session_state['scan_results'])
    
    # Ordenar por fecha
    df_results = df_results.sort_values(by="Fecha", ascending=False)
    df_results['Fecha_Str'] = df_results['Fecha'].dt.strftime('%d-%m-%Y')
    
    # --- TABLA ---
    st.subheader("📋 Resultados Acumulados")
    
    c1, c2 = st.columns([1, 4])
    with c1:
        filter_type = st.multiselect("Filtrar Tipo:", ["🟢 COMPRA", "🔴 VENTA"], default=["🟢 COMPRA", "🔴 VENTA"])
    
    df_show = df_results[df_results['Tipo'].isin(filter_type)] if filter_type else df_results

    def color_signal(val):
        color = '#d4edda' if 'COMPRA' in str(val) else '#f8d7da'
        return f'background-color: {color}; color: black; font-weight: bold'

    st.dataframe(
        df_show.style.applymap(color_signal, subset=['Tipo']),
        column_config={
            "Ticker": "Activo", "Fecha_Str": "Fecha Señal", "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "ADX": st.column_config.NumberColumn(format="%.2f"),
        },
        use_container_width=True, hide_index=True
    )
    
    st.divider()
    
    # --- VISUALIZADOR DE GRÁFICO (CON BACKTESTING) ---
    st.subheader("📉 Backtesting Visual")
    
    available_tickers = df_show['Ticker'].tolist()
    
    if available_tickers:
        selected_ticker = st.selectbox("Selecciona un activo para ver el historial de señales:", available_tickers)
        
        if selected_ticker:
            sig_info = df_show[df_show['Ticker'] == selected_ticker].iloc[0]
            
            with st.spinner("Generando gráfico histórico..."):
                # Recuperamos TODAS las señales y el DF
                _, df_chart, all_signals = analyze_ticker(selected_ticker, interval, period_map[interval], adx_len, adx_th)
            
            if df_chart is not None:
                # Filtrado para visualización
                chart_limit = 200 if interval != "1mo" else 1000
                chart_data = df_chart.tail(chart_limit)
                
                fig = go.Figure()

                # 1. Velas HA
                fig.add_trace(go.Candlestick(
                    x=chart_data.index,
                    open=chart_data['HA_Open'], high=chart_data['HA_High'],
                    low=chart_data['HA_Low'], close=chart_data['HA_Close'],
                    name='Heikin Ashi'
                ))
                
                # 2. Backtesting (Pintar todas las señales)
                if all_signals:
                    df_sig_hist = pd.DataFrame(all_signals)
                    # Filtrar visibles
                    min_date = chart_data.index.min()
                    df_sig_visible = df_sig_hist[df_sig_hist['Fecha'] >= min_date]
                    
                    buys = df_sig_visible[df_sig_visible['Tipo'] == '🟢 COMPRA']
                    sells = df_sig_visible[df_sig_visible['Tipo'] == '🔴 VENTA']
                    
                    if not buys.empty:
                        fig.add_trace(go.Scatter(
                            x=buys['Fecha'], y=buys['Precio'] * 0.95,
                            mode='markers', marker=dict(symbol='triangle-up', size=12, color='blue'),
                            name='Compra Histórica',
                            hovertemplate='<b>COMPRA</b><br>%{x}<br>$%{y:.2f}'
                        ))
                        
                    if not sells.empty:
                        fig.add_trace(go.Scatter(
                            x=sells['Fecha'], y=sells['Precio'] * 1.05,
                            mode='markers', marker=dict(symbol='triangle-down', size=12, color='orange'),
                            name='Venta Histórica',
                            hovertemplate='<b>VENTA</b><br>%{x}<br>$%{y:.2f}'
                        ))

                fig.update_layout(
                    title=f"Historial de Señales: {selected_ticker} ({interval})",
                    xaxis_rangeslider_visible=False,
                    height=600,
                    template="plotly_dark",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Info última señal
                st.info(f"Última Alerta: **{sig_info['Tipo']}** el {sig_info['Fecha_Str']} a ${sig_info['Precio']:.2f} (ADX: {sig_info['ADX']:.2f})")

    else:
        st.info("No hay activos disponibles.")

else:
    st.info("👈 Usa el menú para escanear.")
