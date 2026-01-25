import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | V31.0 ENGINE OVERHAUL")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN (CON PRECARGA DE MERCADOS)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({
        "enableRateLimit": True, 
        "timeout": 45000,
        "options": {"defaultType": "future"}
    })
    try:
        ex.load_markets() # Forzamos carga de símbolos
    except:
        pass
    return ex

@st.cache_data(ttl=600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        # Filtro estricto para pares USDT de Futuros
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 5000]
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS SLY (SINCRONIZACIÓN PINE)
# ─────────────────────────────────────────────
def calculate_sly_logic(df, use_ema=True):
    # Heikin Ashi Exacto
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # MACD (12, 26, 9)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    
    # EMA 200
    ema200 = ta.ema(df['close'], length=200)

    estado = 0
    entry_time = None
    
    # Análisis SLY desde que EMA200 es calculable
    for i in range(1, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        price = df['close'].iloc[i]
        e200 = ema200.iloc[i]
        
        if pd.isna(e200) or pd.isna(h): continue
        
        prev_estado = estado
        # Salida
        if estado == 1 and h < h_prev: estado = 0
        elif estado == -1 and h > h_prev: estado = 0
            
        # Entrada
        if estado == 0:
            f_ema_long = (price > e200) if use_ema else True
            f_ema_short = (price < e200) if use_ema else True
            
            if (ha_color[i] == 1) and (h > h_prev) and f_ema_long:
                estado = 1
            elif (ha_color[i] == -1) and (h < h_prev) and f_ema_short:
                estado = -1
        
        if estado != 0 and estado != prev_estado:
            entry_time = df['dt'].iloc[i]

    return estado, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR CON REINTENTOS
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_offset):
    row_data = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        ohlcv = []
        # Protocolo de 2 intentos para evitar errores de red
        for attempt in range(2):
            try:
                # Bajamos el límite a 250 para máxima compatibilidad
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=250)
                if ohlcv and len(ohlcv) >= 200: break
                time.sleep(0.1)
            except:
                time.sleep(0.2)
        
        if not ohlcv or len(ohlcv) < 201:
            row_data[f"{label} Señal"] = "API NO DATA" if not ohlcv else "POCO HIST."
            row_data[f"{label} Horario"] = "-"
            continue
            
        try:
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            
            state, e_time = calculate_sly_logic(df)
            
            if state == 1:
                row_data[f"{label} Señal"] = "LONG 🟢"
                row_data[f"{label} Horario"] = (e_time + pd.Timedelta(hours=utc_offset)).strftime("%H:%M")
            elif state == -1:
                row_data[f"{label} Señal"] = "SHORT 🔴"
                row_data[f"{label} Horario"] = (e_time + pd.Timedelta(hours=utc_offset)).strftime("%H:%M")
            else:
                row_data[f"{label} Señal"] = "FUERA ⚪"
                row_data[f"{label} Horario"] = "-"
        except:
            row_data[f"{label} Señal"] = "ERROR CALC"
            row_data[f"{label} Horario"] = "-"
            
    return row_data

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SLY DASHBOARD V31.0")

with st.sidebar:
    st.header("Configuración")
    utc_h = st.number_input("UTC Offset", value=-3)
    
    all_pairs = get_active_pairs()
    if all_pairs:
        st.info(f"Pares listados: {len(all_pairs)}")
        batch_size = st.selectbox("Batch", [10, 20, 50], index=1)
        batches = [all_pairs[i:i + batch_size] for i in range(0, len(all_pairs), batch_size)]
        sel_batch = st.selectbox("Seleccionar Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} pares)")
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx + 1) / len(batches[sel_batch]), text=f"Sincronizando {sym}...")
                results.append(analyze_ticker(sym, ex, utc_h))
                time.sleep(0.1)
                
            st.session_state["sniper_results"] = results
            prog.empty()

    if st.button("Limpia Memoria / Reset"):
        st.session_state["sniper_results"] = []
        st.rerun()

if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    def style_logic(val):
        if "LONG" in str(val): return 'background-color: #d4edda; color: #155724; font-weight: bold'
        if "SHORT" in str(val): return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        return ''

    st.dataframe(df_f.style.applymap(style_logic), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione Iniciar. Esta versión tiene reintentos forzados para BTC/ETH.")
