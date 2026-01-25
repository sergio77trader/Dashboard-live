import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE INTERFAZ
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | CRYPTO SNIPER")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; }
    [data-testid="stSidebar"] { width: 300px; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN KUCOIN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 50000]
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS SLY (PINE REPLICA)
# ─────────────────────────────────────────────
def calculate_sly_logic(df, use_ema=True):
    # A. Heikin Ashi Recursivo
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # B. MACD (12, 26, 9)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    
    # C. EMA 200
    ema200 = ta.ema(df['close'], length=200)

    # D. Máquina de Estados (Estado SLY)
    estado = 0
    entry_time = None
    
    # Simulación de velas (Top-Down)
    for i in range(1, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        price = df['close'].iloc[i]
        e200 = ema200.iloc[i]
        
        if np.isnan(e200) or np.isnan(h): continue

        # Salidas
        if estado == 1 and h < h_prev: estado = 0
        if estado == -1 and h > h_prev: estado = 0
            
        # Entradas
        if estado == 0:
            f_ema_long = (price > e200) if use_ema else True
            f_ema_short = (price < e200) if use_ema else True
            
            long_cond = (ha_color[i] == 1) and (h > h_prev) and f_ema_long
            short_cond = (ha_color[i] == -1) and (h < h_prev) and f_ema_short
            
            if long_cond:
                estado = 1
                entry_time = df['dt'].iloc[i]
            elif short_cond:
                estado = -1
                entry_time = df['dt'].iloc[i]

    return estado, entry_time

# ─────────────────────────────────────────────
# ANÁLISIS DE MERCADO
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_offset):
    row_data = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        try:
            # Pedimos 400 velas para que la EMA 200 sea estable
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=400)
            if len(ohlcv) < 201: 
                row_data[f"{label} Señal"] = "FALTA DATA"
                row_data[f"{label} Horario"] = "-"
                continue
                
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            
            state, e_time = calculate_sly_logic(df)
            
            # Formateo visual
            if state == 1:
                row_data[f"{label} Señal"] = "LONG 🟢"
                row_data[f"{label} Horario"] = (e_time + pd.Timedelta(hours=utc_offset)).strftime("%d/%m %H:%M")
            elif state == -1:
                row_data[f"{label} Señal"] = "SHORT 🔴"
                row_data[f"{label} Horario"] = (e_time + pd.Timedelta(hours=utc_offset)).strftime("%d/%m %H:%M")
            else:
                row_data[f"{label} Señal"] = "FUERA ⚪"
                row_data[f"{label} Horario"] = "-"
        except:
            row_data[f"{label} Señal"] = "ERROR"
            row_data[f"{label} Horario"] = "-"
            
    return row_data

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────
st.title("🎯 Dashboard SLY: Crypto Sniper")

with st.sidebar:
    st.header("Configuración")
    utc_h = st.number_input("Diferencia Horaria (UTC)", value=-3)
    
    all_pairs = get_active_pairs()
    if all_pairs:
        st.success(f"Mercado KuCoin: {len(all_pairs)} pares")
        batch_size = st.selectbox("Tamaño de Escaneo", [10, 20, 50, 100], index=1)
        batches = [all_pairs[i:i + batch_size] for i in range(0, len(all_pairs), batch_size)]
        sel_batch = st.selectbox("Seleccionar Lote", range(len(batches)))
        
        if st.button("🚀 ESCANEAR ACTIVOS", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx + 1) / len(batches[sel_batch]), text=f"Analizando {sym}")
                res = analyze_ticker(sym, ex, utc_h)
                results.append(res)
                time.sleep(0.1) # Evitar Rate Limit
                
            st.session_state["sniper_results"] = results
            prog.empty()

    if st.button("Limpiar Tabla"):
        st.session_state["sniper_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE TABLA
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Estilo de colores
    def color_signals(val):
        if "LONG" in str(val): return 'background-color: #d1f2eb; color: #1b5e20; font-weight: bold'
        if "SHORT" in str(val): return 'background-color: #fdedec; color: #b71c1c; font-weight: bold'
        if "FUERA" in str(val): return 'color: #7f8c8d'
        return ''

    st.dataframe(df_final.style.applymap(color_signals), use_container_width=True, height=800)
else:
    st.info("👈 Selecciona un lote de criptomonedas y presiona 'Escanear' para ver las señales SLY.")
