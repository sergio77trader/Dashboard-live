import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - KuCoin Matrix Pro")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# --- MEMORIA ---
if 'crypto_results' not in st.session_state:
    st.session_state['crypto_results'] = []

# --- MAPEO TEMPORAL ---
TIMEFRAMES_HA = {'1H': '1h', '4H': '4h', 'Diario': '1d', 'Semanal': '1w', 'Mensual': '1M'}
TIMEFRAMES_RSI = {'15m': '15m', '1H': '1h', '4H': '4h', '12H': '12h', '1D': '1d', '1W': '1w'}

# --- FUNCIONES MATEMÁTICAS ---
def calculate_heikin_ashi(df):
    if df is None or df.empty or len(df) < 2: return pd.DataFrame()
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df_ha['HA_Open'] = 0.0
    df_ha.iat[0, df_ha.columns.get_loc('HA_Open')] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
    vals = df_ha.values
    idx_open, idx_close = df_ha.columns.get_loc('HA_Open'), df_ha.columns.get_loc('HA_Close')
    for i in range(1, len(vals)):
        vals[i, idx_open] = (vals[i-1, idx_open] + vals[i-1, idx_close]) / 2
    df_ha['HA_Open'] = vals[:, idx_open]
    return df_ha

def calculate_rsi(df, length=14):
    """Calcula el último valor del RSI"""
    if df.empty or len(df) < length: return 50.0
    try:
        rsi = df.ta.rsi(length=length)
        return rsi.iloc[-1] if rsi is not None else 50.0
    except: return 50.0

# --- MOTORES DE DATOS ---
@st.cache_data(ttl=3600)
def get_active_pairs():
    try:
        exchange = ccxt.kucoinfutures({'enableRateLimit': True})
        markets = exchange.load_markets()
        valid = [s for s in markets if markets[s]['quote'] == 'USDT' and markets[s]['active']]
        majors = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT', 'BNB/USDT:USDT']
        return [p for p in majors if p in valid] + sorted([p for p in valid if p not in majors])
    except: return []

def scan_batch_ha(targets):
    exchange = ccxt.kucoinfutures({'enableRateLimit': True, 'timeout': 30000})
    results = []
    prog = st.progress(0, text="Escaneando Tendencias...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"Tendencia: {symbol}")
        row = {'Activo': symbol.replace(':USDT', ''), 'Symbol_Raw': symbol}
        greens = 0
        valid_tfs = 0
        
        for tf_lbl, tf_code in TIMEFRAMES_HA.items():
            try:
                limit = 12 if tf_code == '1M' else 30
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit)
                if not ohlcv or len(ohlcv) < 2:
                    row[tf_lbl] = "⚪"
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
                df_ha = calculate_heikin_ashi(df)
                last = df_ha.iloc[-1]
                
                if last['HA_Close'] >= last['HA_Open']:
                    row[tf_lbl] = "🟢"
                    greens += 1
                else:
                    row[tf_lbl] = "🔴"
                valid_tfs += 1
            except: row[tf_lbl] = "⚠️"
        
        if valid_tfs > 0:
            ratio = greens / valid_tfs
            if ratio == 1.0: row['Diagnóstico'] = "🔥 FULL ALCISTA"
            elif ratio == 0.0: row['Diagnóstico'] = "❄️ FULL BAJISTA"
            elif ratio >= 0.75: row['Diagnóstico'] = "✅ ALCISTA FUERTE"
            elif ratio <= 0.25: row['Diagnóstico'] = "🔻 BAJISTA FUERTE"
            else: row['Diagnóstico'] = "⚖️ MIXTO"
            results.append(row)
        
        time.sleep(0.2)
    prog.empty()
    return pd.DataFrame(results)

def scan_rsi_deep(targets):
    """Escaneo profundo de RSI para monedas seleccionadas"""
    exchange = ccxt.kucoinfutures({'enableRateLimit': True, 'timeout': 30000})
    results = []
    prog = st.progress(0, text="Calculando RSI Matrix...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"RSI: {symbol}")
        clean_name = symbol.replace(':USDT', '')
        row = {'Activo': clean_name}
        
        for tf_lbl, tf_code in TIMEFRAMES_RSI.items():
            try:
                # Descargamos velas normales (no HA) para el RSI
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=30)
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
                    rsi_val = calculate_rsi(df)
                    row[f'RSI {tf_lbl}'] = rsi_val
                else:
                    row[f'RSI {tf_lbl}'] = 50.0
            except:
                row[f'RSI {tf_lbl}'] = 50.0
        
        results.append(row)
        time.sleep(0.25) # Pausa para no saturar
        
    prog.empty()
    return pd.DataFrame(results)

# --- UI PRINCIPAL ---
st.title("⚡ SystemaTrader: KuCoin Matrix Pro")

# --- SIDEBAR (CONFIGURACIÓN) ---
with st.sidebar:
    if st.button("🔄 Recargar Mercado"):
        st.cache_data.clear()
        
    all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        st.divider()
        st.header("1. Escaneo de Tendencia")
        
        BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 50], index=1)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        batch_opts = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
        sel_batch = st.selectbox("Elegir Lote:", range(len(batches)), format_func=lambda x: batch_opts[x])
        accumulate = st.checkbox("Acumular Resultados", value=True)
        
        if st.button("🚀 ESCANEAR LOTE", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Analizando estructura Heikin Ashi..."):
                new_df = scan_batch_ha(target)
                if not new_df.empty:
                    new_data = new_df.to_dict('records')
                    if accumulate:
                        existing = {x['Activo'] for x in st.session_state['crypto_results']}
                        for item in new_data:
                            if item['Activo'] not in existing:
                                st.session_state['crypto_results'].append(item)
                    else:
                        st.session_state['crypto_results'] = new_data
                    st.success("Lote procesado.")
        
        if st.button("Limpiar Tabla"):
            st.session_state['crypto_results'] = []
            st.rerun()
    else:
        st.error("Error de conexión.")

# --- SECCIÓN 1: TABLA DE TENDENCIAS (ACUMULATIVA) ---
if st.session_state['crypto_results']:
    df = pd.DataFrame(st.session_state['crypto_results'])
    
    # Filtros
    f_col1, f_col2 = st.columns([3, 1])
    with f_col1:
        f_mode = st.radio("Filtro Tendencia:", ["Todos", "🔥 Oportunidades"], horizontal=True)
    
    if f_mode == "🔥 Oportunidades":
        df = df[df['Diagnóstico'].isin(["🔥 FULL ALCISTA", "❄️ FULL BAJISTA"])]
    
    # Ordenamiento
    sort_map = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
    df['sort'] = df['Diagnóstico'].map(sort_map).fillna(5)
    df = df.sort_values('sort').drop('sort', axis=1)

    st.subheader("1. Radar de Tendencia (Heikin Ashi)")
    st.dataframe(
        df,
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small"),
            "1H": st.column_config.TextColumn("1H", width="small"),
            "4H": st.column_config.TextColumn("4H", width="small"),
            "Diario": st.column_config.TextColumn("D", width="small"),
            "Semanal": st.column_config.TextColumn("S", width="small"),
            "Mensual": st.column_config.TextColumn("M", width="small"),
            "Diagnóstico": st.column_config.TextColumn("Estructura", width="medium"),
            "Symbol_Raw": None
        },
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.divider()

    # --- SECCIÓN 2: ANÁLISIS RSI PROFUNDO (NUEVO) ---
    st.subheader("2. Microscopio de Momentum (RSI)")
    st.info("Selecciona las criptomonedas de la lista de arriba que te interesen para ver su RSI detallado.")

    # Obtenemos lista limpia de activos encontrados
    available_assets = df['Activo'].tolist()
    # Mapeo inverso para obtener el symbol raw
    raw_map = {item['Activo']: item['Symbol_Raw'] for item in st.session_state['crypto_results']}
    
    selected_assets = st.multiselect("Seleccionar Activos para Análisis RSI:", available_assets)
    
    if st.button("🔎 ANALIZAR RSI (SELECCIONADOS)"):
        if selected_assets:
            # Recuperar symbols técnicos
            target_raws = [raw_map[a] for a in selected_assets]
            
            with st.spinner("Calculando RSI en 6 temporalidades..."):
                df_rsi = scan_rsi_deep(target_raws)
                
                if not df_rsi.empty:
                    st.dataframe(
                        df_rsi,
                        column_config={
                            "Activo": st.column_config.TextColumn("Activo", width="small"), # Fixed removido aquí
                            "RSI 15m": st.column_config.NumberColumn("15m", format="%.1f"),
                            "RSI 1H": st.column_config.NumberColumn("1H", format="%.1f"),
                            "RSI 4H": st.column_config.NumberColumn("4H", format="%.1f"),
                            "RSI 12H": st.column_config.NumberColumn("12H", format="%.1f"),
                            "RSI 1D": st.column_config.NumberColumn("Diario", format="%.1f"),
                            "RSI 1W": st.column_config.NumberColumn("Semanal", format="%.1f"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    st.caption("Referencias: Valores > 70 (Sobrecompra) | Valores < 30 (Sobreventa)")
                else:
                    st.error("Error al obtener datos RSI.")
        else:
            st.warning("Por favor selecciona al menos un activo de la lista.")

else:
    st.info("👈 Comienza escaneando un lote en la barra lateral.")
