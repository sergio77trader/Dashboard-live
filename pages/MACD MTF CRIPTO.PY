import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MACD Zero Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #00CC96; }
</style>
""", unsafe_allow_html=True)

# --- MAPEO TEMPORAL ---
# KuCoin via CCXT soporta estos timeframes
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w',
    'Mensual': '1M'
}

# --- MOTOR DE CONEXIÓN (KUCOIN FUTURES) ---
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })

@st.cache_data(ttl=3600)
def get_active_pairs():
    """Obtiene Top monedas por volumen en KuCoin"""
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s in tickers:
            if '/USDT:USDT' in s and tickers[s]['quoteVolume']:
                valid.append({
                    'symbol': s, 
                    'vol': tickers[s]['quoteVolume']
                })
        
        # Ordenar por volumen descendente
        df = pd.DataFrame(valid).sort_values('vol', ascending=False)
        return df['symbol'].tolist()
    except:
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

# --- LÓGICA MACD ---
def check_macd_level(df, fast=12, slow=26, sig=9):
    """
    Determina si el MACD está en zona Alcista (>0) o Bajista (<0).
    Retorna: Valor numérico y Estado
    """
    if df.empty or len(df) < 35: return 0, "N/A"
    
    try:
        macd_df = df.ta.macd(fast=fast, slow=slow, signal=sig)
        if macd_df is None: return 0, "N/A"
        
        # MACD Line es la columna 'MACD_12_26_9'
        col_name = f'MACD_{fast}_{slow}_{sig}'
        macd_val = macd_df[col_name].iloc[-1]
        
        state = "🟢 Sobre 0" if macd_val > 0 else "🔴 Bajo 0"
        return macd_val, state
    except:
        return 0, "N/A"

def scan_macd_matrix(targets):
    exchange = get_exchange()
    results = []
    
    prog = st.progress(0, text="Escaneando Estructura MACD...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        clean_name = symbol.replace(':USDT', '').replace('/USDT', '')
        prog.progress((idx)/total, text=f"Analizando {clean_name}...")
        
        row = {'Activo': clean_name}
        bullish_count = 0
        valid_count = 0
        
        for label, tf_code in TIMEFRAMES.items():
            try:
                # Pedimos suficientes velas para que el MACD se estabilice
                limit = 60 if tf_code == '1M' else 100
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit)
                
                if not ohlcv:
                    row[label] = "⚪" # Sin datos
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                val, state = check_macd_level(df)
                
                # Guardamos solo el icono para la tabla
                if state == "N/A":
                    row[label] = "⚪"
                elif val > 0:
                    row[label] = "🟢" # Arriba de 0
                    bullish_count += 1
                    valid_count += 1
                else:
                    row[label] = "🔴" # Abajo de 0
                    valid_count += 1
                    
            except:
                row[label] = "⚠️"
        
        # Diagnóstico de Estructura
        if valid_count > 0:
            if bullish_count == valid_count:
                row['Estructura'] = "🔥 FULL BULL (Todos > 0)"
            elif bullish_count == 0:
                row['Estructura'] = "❄️ FULL BEAR (Todos < 0)"
            elif bullish_count >= 3:
                row['Estructura'] = "✅ Mayoría Alcista"
            else:
                row['Estructura'] = "🔻 Mayoría Bajista"
        else:
            row['Estructura'] = "-"

        results.append(row)
        time.sleep(0.15) # Rate limit
        
    prog.empty()
    return pd.DataFrame(results)

# --- INTERFAZ ---
st.title("🎛️ SystemaTrader: MACD Zero Matrix")
st.markdown("""
**Objetivo:** Identificar la ubicación de las líneas MACD respecto al nivel 0.
*   **Sobre 0 (🟢):** Tendencia de fondo Alcista. Solo buscar compras.
*   **Bajo 0 (🔴):** Tendencia de fondo Bajista. Solo buscar ventas.
""")

# --- MEMORIA ---
if 'macd_results' not in st.session_state:
    st.session_state['macd_results'] = []

with st.sidebar:
    st.header("Configuración")
    
    with st.spinner("Cargando mercado..."):
        all_symbols = get_active_pairs()
    
    st.success(f"Mercado: {len(all_symbols)} activos")
    
    # Lotes
    BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 30], index=1)
    batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    batch_labels = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        # Filtrar duplicados
        existing = {x['Activo'] for x in st.session_state['macd_results']}
        # Ajuste nombre para filtro (Kucoin usa :USDT)
        to_run = [t for t in targets if t.replace(':USDT', '').replace('/USDT', '') not in existing]
        
        if to_run:
            new_data = scan_macd_matrix(to_run)
            st.session_state['macd_results'].extend(new_data.to_dict('records'))
            st.success("Datos agregados.")
        else:
            st.warning("Lote ya escaneado.")

    if c2.button("🗑️ Limpiar"):
        st.session_state['macd_results'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['macd_results']:
    df = pd.DataFrame(st.session_state['macd_results'])
    
    # Ordenar
    sort_map = {"🔥 FULL BULL (Todos > 0)": 0, "❄️ FULL BEAR (Todos < 0)": 1, "✅ Mayoría Alcista": 2, "🔻 Mayoría Bajista": 3, "-": 4}
    df['sort'] = df['Estructura'].map(sort_map).fillna(5)
    df = df.sort_values('sort').drop('sort', axis=1)
    
    # Filtro Visual
    ver = st.radio("Filtro:", ["Todos", "Solo Full Bull/Bear"], horizontal=True)
    if ver == "Solo Full Bull/Bear":
        df = df[df['Estructura'].str.contains("FULL")]

    st.dataframe(
        df,
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small", pinned=True),
            "1H": st.column_config.TextColumn("1H", width="small"),
            "4H": st.column_config.TextColumn("4H", width="small"),
            "Diario": st.column_config.TextColumn("D", width="small"),
            "Semanal": st.column_config.TextColumn("S", width="small"),
            "Mensual": st.column_config.TextColumn("M", width="small"),
            "Estructura": st.column_config.TextColumn("Contexto Global", width="medium"),
        },
        use_container_width=True,
        hide_index=True,
        height=700
    )
else:
    st.info("👈 Selecciona un lote para analizar la estructura del mercado.")
