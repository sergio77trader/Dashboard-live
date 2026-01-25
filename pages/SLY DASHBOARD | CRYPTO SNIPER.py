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
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | V38.0 MOMENTUM")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stProgress > div > div > div > div { background-color: #00E676; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN (LIGERO)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        "enableRateLimit": True, 
        "timeout": 30000,
        "options": {"defaultType": "future"}
    })

@st.cache_data(ttl=600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 10000]
    except: return []

# ─────────────────────────────────────────────
# NÚCLEO LÓGICO SLY (SOLO MOMENTUM)
# ─────────────────────────────────────────────
def run_sly_momentum_engine(df, use_zero):
    # 1. MACD (12, 26, 9) - Converge rápido
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, None
    hist = macd['MACDh_12_26_9']

    # 2. Heikin Ashi Recursivo (Precisión Pine)
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # 3. Máquina de Estados
    estado = 0
    entry_time = None
    
    # Empezamos en la vela 50 para asegurar estabilidad de MACD
    for i in range(50, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        
        prev_estado = estado

        # Salidas SLY (Giro de Histograma)
        if estado == 1 and h < h_prev: estado = 0
        elif estado == -1 and h > h_prev: estado = 0
            
        # Entradas (Sin Filtro EMA)
        if estado == 0:
            f_zero_long = (h < 0) if use_zero else True
            f_zero_short = (h > 0) if use_zero else True
            
            if (ha_color[i] == 1) and (h > h_prev) and f_zero_long:
                estado = 1
            elif (ha_color[i] == -1) and (h < h_prev) and f_zero_short:
                estado = -1
        
        if estado != 0 and estado != prev_estado:
            entry_time = df['dt'].iloc[i]

    return estado, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR MTF
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_h, use_zero):
    row = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        try:
            # SÓLO PEDIMOS 200 VELAS: Máxima estabilidad de API
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
            
            if not ohlcv or len(ohlcv) < 100:
                row[f"{label} Señal"] = "SIN DATA"
                row[f"{label} Horario"] = "-"
                continue
                
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            
            st_val, tm_val = run_sly_momentum_engine(df, use_zero)
            
            if st_val == 1:
                row[f"{label} Señal"] = "LONG 🟢"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M")
            elif st_val == -1:
                row[f"{label} Señal"] = "SHORT 🔴"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M")
            else:
                row[f"{label} Señal"] = "FUERA ⚪"
                row[f"{label} Horario"] = "-"
            
            time.sleep(0.02) # Pausa mínima
            
        except:
            row[f"{label} Señal"] = "ERROR"
            row[f"{label} Horario"] = "-"
            
    return row

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────
st.title("🎯 SLY MOMENTUM SNIPER V38")

with st.sidebar:
    st.header("Configuración")
    u_zero = st.checkbox("Filtro Cruce Cero (MACD)", value=False)
    utc_val = st.number_input("Horario UTC", value=-3)
    
    st.divider()
    all_pairs = get_active_pairs()
    if all_pairs:
        st.success(f"Mercado: {len(all_pairs)} activos")
        b_size = st.selectbox("Batch Size", [20, 50, 100], index=1)
        batches = [all_pairs[i:i+b_size] for i in range(0, len(all_pairs), b_size)]
        sel_batch = st.selectbox("Seleccionar Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} pares)")
        
        if st.button("🚀 ESCANEAR RÁPIDO", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx+1)/len(batches[sel_batch]), text=f"Analizando {sym}...")
                results.append(analyze_ticker(sym, ex, utc_val, u_zero))
                
            st.session_state["sniper_results"] = results
            prog.empty()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# RENDERIZADO
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    def color_cells(val):
        if "LONG" in str(val): return 'background-color: #d4edda; color: #155724; font-weight: bold'
        if "SHORT" in str(val): return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        return ''

    st.dataframe(df_f.style.applymap(color_cells), use_container_width=True, height=800)
else:
    st.info("👈 Presiona 'ESCANEAR RÁPIDO'. Sin EMA 200, el sistema sincronizará los giros de MACD/HA al instante.")
