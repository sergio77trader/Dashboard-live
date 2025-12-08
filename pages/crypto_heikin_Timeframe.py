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

# Definimos qué métricas sacar para cada TF en el análisis profundo
# Tupla: (Label, CCXT Code, Calcular RSI?, Calcular Cambio Precio?, Calcular Cambio Vol?)
DEEP_TASKS = [
    ('15m', '15m', True, False, False), # Solo RSI
    ('1H',  '1h',  True, True,  True),  # Todo
    ('4H',  '4h',  True, True,  True),  # Todo
    ('12H', '12h', True, True,  False), # RSI + Precio
    ('1D',  '1d',  True, True,  True),  # Todo (24h)
    ('1W',  '1w',  True, False, False)  # Solo RSI
]

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

def get_metrics(df, length=14):
    """Calcula RSI, Variación Precio y Variación Volumen"""
    metrics = {'rsi': 50.0, 'p_chg': 0.0, 'v_chg': 0.0}
    if df.empty: return metrics
    
    try:
        # RSI
        rsi = df.ta.rsi(length=length)
        metrics['rsi'] = rsi.iloc[-1] if rsi is not None else 50.0
        
        # Precio y Volumen (Ultima vela)
        curr = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else curr
        
        # % Variación Precio (Intra-vela: Cierre vs Apertura)
        if curr['open'] > 0:
            metrics['p_chg'] = ((curr['close'] - curr['open']) / curr['open']) * 100
            
        # % Variación Volumen (Vs vela anterior)
        if prev['vol'] > 0:
            metrics['v_chg'] = ((curr['vol'] - prev['vol']) / prev['vol']) * 100
            
    except: pass
    return metrics

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

def scan_deep_metrics(targets):
    """Escaneo profundo: RSI + Precio + Volumen"""
    exchange = ccxt.kucoinfutures({'enableRateLimit': True, 'timeout': 30000})
    results = []
    prog = st.progress(0, text="Analizando Métricas...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"Analizando: {symbol}")
        clean_name = symbol.replace(':USDT', '')
        row = {'Activo': clean_name}
        
        for lbl, tf, get_rsi, get_price, get_vol in DEEP_TASKS:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
                if ohlcv:
                    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
                    m = get_metrics(df)
                    
                    if get_rsi: row[f'RSI {lbl}'] = m['rsi']
                    if get_price: row[f'P% {lbl}'] = m['p_chg']
                    if get_vol: row[f'V% {lbl}'] = m['v_chg']
                else:
                    if get_rsi: row[f'RSI {lbl}'] = 50.0
            except:
                pass # Si falla, queda vacío
        
        results.append(row)
        time.sleep(0.25) # Pausa necesaria
        
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

# --- SECCIÓN 1: TABLA DE TENDENCIAS ---
if st.session_state['crypto_results']:
    df = pd.DataFrame(st.session_state['crypto_results'])
    
    f_col1, f_col2 = st.columns([3, 1])
    with f_col1:
        f_mode = st.radio("Filtro Tendencia:", ["Todos", "🔥 Oportunidades"], horizontal=True)
    
    if f_mode == "🔥 Oportunidades":
        df = df[df['Diagnóstico'].isin(["🔥 FULL ALCISTA", "❄️ FULL BAJISTA"])]
    
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
        use_container_width=True, hide_index=True, height=400
    )

    st.divider()

    # --- SECCIÓN 2: ANÁLISIS PROFUNDO (RSI + PRECIO + VOLUMEN) ---
    st.subheader("2. Microscopio Táctico (RSI | Precio | Volumen)")
    st.info("Selecciona activos para ver: RSI (15m-1W), Variación Precio % (1h, 4h, 24h) y Variación Volumen % (1h, 4h, 24h).")

    available_assets = df['Activo'].tolist()
    raw_map = {item['Activo']: item['Symbol_Raw'] for item in st.session_state['crypto_results']}
    
    selected_assets = st.multiselect("Seleccionar Activos:", available_assets)
    
    if st.button("🔎 ANALIZAR A FONDO"):
        if selected_assets:
            target_raws = [raw_map[a] for a in selected_assets]
            
            with st.spinner("Calculando Métricas Avanzadas..."):
                df_deep = scan_deep_metrics(target_raws)
                
                if not df_deep.empty:
                    # Relleno de NaNs para evitar errores de renderizado
                    df_deep = df_deep.fillna(0.0)
                    
                    st.dataframe(
                        df_deep,
                        column_config={
                            "Activo": st.column_config.TextColumn("Activo", width="small"),
                            # RSI Config
                            "RSI 15m": st.column_config.NumberColumn("RSI 15m", format="%.0f"),
                            "RSI 1H": st.column_config.NumberColumn("RSI 1h", format="%.0f"),
                            "RSI 4H": st.column_config.NumberColumn("RSI 4h", format="%.0f"),
                            "RSI 12H": st.column_config.NumberColumn("RSI 12h", format="%.0f"),
                            "RSI 1D": st.column_config.NumberColumn("RSI 1d", format="%.0f"),
                            
                            # Precio Config (P% = Price Change %)
                            "P% 1H": st.column_config.NumberColumn("P% 1H", format="%.2f%%"),
                            "P% 4H": st.column_config.NumberColumn("P% 4H", format="%.2f%%"),
                            "P% 1D": st.column_config.NumberColumn("P% 24H", format="%.2f%%"),
                            
                            # Volumen Config (V% = Volume Change %)
                            "V% 1H": st.column_config.NumberColumn("V% 1H", format="%.2f%%"),
                            "V% 4H": st.column_config.NumberColumn("V% 4H", format="%.2f%%"),
                            "V% 1D": st.column_config.NumberColumn("V% 24H", format="%.2f%%"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    st.caption("""
                    **Referencias:**
                    *   **RSI:** >70 Sobrecompra | <30 Sobreventa.
                    *   **P% (Precio):** Variación dentro de la vela actual.
                    *   **V% (Volumen):** Variación respecto a la vela anterior.
                    """)
                else:
                    st.error("Error al obtener datos.")
        else:
            st.warning("Selecciona al menos un activo.")

else:
    st.info("👈 Escanea un lote para comenzar.")
