import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MACD Zero Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #00CC96; }
</style>
""", unsafe_allow_html=True)

# --- MAPEO TEMPORAL ---
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w',
    'Mensual': '1M'
}

# --- CONEXIÓN ---
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })

@st.cache_data(ttl=3600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s in tickers:
            # Filtro: USDT Perpetuos con volumen real
            if '/USDT:USDT' in s and tickers[s]['quoteVolume']:
                valid.append({'symbol': s, 'vol': tickers[s]['quoteVolume']})
        
        # Ordenar por volumen descendente (Liquidez)
        df = pd.DataFrame(valid).sort_values('vol', ascending=False)
        return df['symbol'].tolist()
    except:
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

# --- LÓGICA MACD ---
def get_macd_data(df, fast=12, slow=26, sig=9):
    """Retorna valor MACD Line y Estado"""
    if df.empty or len(df) < 35: return 0.0, "N/A"
    
    try:
        macd_df = df.ta.macd(fast=fast, slow=slow, signal=sig)
        if macd_df is None: return 0.0, "N/A"
        
        # MACD Line
        col_name = f'MACD_{fast}_{slow}_{sig}'
        macd_val = macd_df[col_name].iloc[-1]
        
        # Sanitizar NaN
        if pd.isna(macd_val): return 0.0, "N/A"
        
        state = "BULL" if macd_val > 0 else "BEAR"
        return float(macd_val), state
    except:
        return 0.0, "N/A"

def scan_macd_matrix(targets):
    exchange = get_exchange()
    results = []
    
    # Barra de progreso
    prog = st.progress(0, text="Iniciando motor de análisis...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        clean_name = symbol.replace(':USDT', '').replace('/USDT', '')
        
        # Actualizamos texto de progreso
        prog.progress((idx)/total, text=f"Analizando {clean_name} ({idx+1}/{total})...")
        
        row = {'Activo': clean_name}
        bull_count = 0
        valid_count = 0
        
        for label, tf_code in TIMEFRAMES.items():
            try:
                # Límites ajustados para velocidad
                limit = 50 if tf_code == '1M' else 80
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit)
                
                if not ohlcv:
                    row[label] = 0.0
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                val, state = get_macd_data(df)
                
                # Guardamos valor numérico
                row[label] = val
                
                if state == "BULL":
                    bull_count += 1
                    valid_count += 1
                elif state == "BEAR":
                    valid_count += 1
                    
            except:
                row[label] = 0.0
        
        # Diagnóstico Estructural
        if valid_count > 0:
            if bull_count == valid_count: row['Estructura'] = "🔥 FULL BULL"
            elif bull_count == 0: row['Estructura'] = "❄️ FULL BEAR"
            elif bull_count >= 3: row['Estructura'] = "✅ Mayoría Alcista"
            else: row['Estructura'] = "🔻 Mayoría Bajista"
        else:
            row['Estructura'] = "-"

        results.append(row)
        # Pausa táctica levemente reducida para compensar volumen
        time.sleep(0.12)
        
    prog.empty()
    return pd.DataFrame(results)

# --- UI ---
st.title("🎛️ SystemaTrader: MACD Zero Matrix")
st.caption("Valores positivos = Sobre 0 (Tendencia Alcista) | Valores negativos = Bajo 0 (Tendencia Bajista)")

if 'macd_vals' not in st.session_state:
    st.session_state['macd_vals'] = []

with st.sidebar:
    st.header("Control")
    
    with st.spinner("Cargando mercado..."):
        all_symbols = get_active_pairs()
    
    st.success(f"Mercado: {len(all_symbols)} activos")
    
    # --- MODIFICACIÓN AQUÍ: SELECTOR EXPANDIDO ---
    BATCH_SIZE = st.selectbox("Tamaño Lote:", [30, 50, 100], index=0)
    
    if BATCH_SIZE == 100:
        st.warning("⚠️ El escaneo de 100 activos tardará unos 3 minutos. Ten paciencia.")
        
    batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    batch_labels = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    if st.button("🚀 ESCANEAR VALORES", type="primary"):
        targets = batches[sel_batch]
        # Filtramos los que ya tenemos para no perder tiempo
        existing = {x['Activo'] for x in st.session_state['macd_vals']}
        to_run = [t for t in targets if t.replace(':USDT', '').replace('/USDT', '') not in existing]
        
        if to_run:
            new_data = scan_macd_matrix(to_run)
            st.session_state['macd_vals'].extend(new_data.to_dict('records'))
            st.success(f"Procesados {len(to_run)} nuevos activos.")
        else:
            st.warning("Este lote ya está cargado.")

    if st.button("🗑️ Limpiar"):
        st.session_state['macd_vals'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['macd_vals']:
    df = pd.DataFrame(st.session_state['macd_vals'])
    
    # Ordenar por estructura
    sort_map = {"🔥 FULL BULL": 0, "❄️ FULL BEAR": 1, "✅ Mayoría Alcista": 2, "🔻 Mayoría Bajista": 3, "-": 4}
    df['sort'] = df['Estructura'].map(sort_map).fillna(5)
    df = df.sort_values('sort').drop('sort', axis=1)

    # Función de estilo
    def style_macd(val):
        if isinstance(val, (int, float)):
            if val > 0: return 'color: #00FF00; font-weight: bold; background-color: rgba(0,255,0,0.1)'
            if val < 0: return 'color: #FF4500; font-weight: bold; background-color: rgba(255,0,0,0.1)'
        return ''

    st.dataframe(
        df.style.applymap(style_macd, subset=['1H', '4H', 'Diario', 'Semanal', 'Mensual']),
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small", pinned=True),
            "1H": st.column_config.NumberColumn("1H", format="%.2f"),
            "4H": st.column_config.NumberColumn("4H", format="%.2f"),
            "Diario": st.column_config.NumberColumn("1D", format="%.2f"),
            "Semanal": st.column_config.NumberColumn("1S", format="%.2f"),
            "Mensual": st.column_config.NumberColumn("1M", format="%.2f"),
            "Estructura": st.column_config.TextColumn("Contexto", width="medium"),
        },
        use_container_width=True,
        hide_index=True,
        height=700
    )
else:
    st.info("👈 Escanea un lote para ver los valores del MACD.")
