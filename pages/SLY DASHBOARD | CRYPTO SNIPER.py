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
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | V35.0 FINAL")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (CONEXIÓN SEGURA)
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
        # Filtro de volumen para asegurar que el activo tenga velas
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 5000]
    except: return []

# ─────────────────────────────────────────────
# LÓGICA SLY (REPLICA EXACTA PINE)
# ─────────────────────────────────────────────
def run_sly_engine(df, use_ema):
    # 1. EMA Adaptativa (Si no hay 200 velas, usamos el máximo disponible)
    length_ema = 200 if len(df) >= 200 else len(df) // 2
    ema_val = ta.ema(df['close'], length=max(length_ema, 10))
    
    # 2. MACD (12, 26, 9)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, None
    hist = macd['MACDh_12_26_9']

    # 3. Heikin Ashi Recursivo
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # 4. Máquina de Estados (State Machine)
    estado = 0
    entry_time = None
    
    # Iniciamos el loop desde la vela 34 (mínimo para MACD)
    for i in range(34, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        price = df['close'].iloc[i]
        e_v = ema_val.iloc[i] if ema_val is not None else price
        
        prev_estado = estado

        # Salidas
        if estado == 1 and h < h_prev: estado = 0
        elif estado == -1 and h > h_prev: estado = 0
            
        # Entradas
        if estado == 0:
            f_ema_long = (price > e_v) if use_ema else True
            f_ema_short = (price < e_v) if use_ema else True
            
            if (ha_color[i] == 1) and (h > h_prev) and f_ema_long:
                estado = 1
            elif (ha_color[i] == -1) and (h < h_prev) and f_ema_short:
                estado = -1
        
        # Guardar hora del primer cambio
        if estado != 0 and estado != prev_estado:
            entry_time = df['dt'].iloc[i]

    return estado, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR MTF
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_h, use_ema):
    row = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        try:
            # LÍMITE DE 200 PARA MÁXIMA COMPATIBILIDAD CON KUCOIN
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
            
            if not ohlcv or len(ohlcv) < 50:
                row[f"{label} Señal"] = "SIN DATA"
                row[f"{label} Horario"] = "-"
                continue
                
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            
            st_val, tm_val = run_sly_engine(df, use_ema)
            
            if st_val == 1:
                row[f"{label} Señal"] = "LONG 🟢"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M") if tm_val else "Ahora"
            elif st_val == -1:
                row[f"{label} Señal"] = "SHORT 🔴"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M") if tm_val else "Ahora"
            else:
                row[f"{label} Señal"] = "FUERA ⚪"
                row[f"{label} Horario"] = "-"
        except:
            row[f"{label} Señal"] = "API ERR"
            row[f"{label} Horario"] = "-"
            
    return row

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────
st.title("🎯 SLY DASHBOARD | V35.0 FINAL")

with st.sidebar:
    st.header("Configuración")
    u_ema = st.checkbox("Filtro EMA 200", value=True)
    utc_val = st.number_input("UTC Offset (Arg=-3)", value=-3)
    
    st.divider()
    all_pairs = get_active_pairs()
    if all_pairs:
        st.success(f"Mercado: {len(all_pairs)} activos")
        b_size = st.selectbox("Batch Size", [10, 20, 50], index=1)
        batches = [all_pairs[i:i+b_size] for i in range(0, len(all_pairs), b_size)]
        sel_batch = st.selectbox("Seleccionar Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} pares)")
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx+1)/len(batches[sel_batch]), text=f"Analizando {sym}...")
                results.append(analyze_ticker(sym, ex, utc_val, u_ema))
                time.sleep(0.05) # Delay anti-bloqueo
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
    st.info("👈 Selecciona un lote y presiona el botón. Esta versión está optimizada para saltar los bloqueos de KuCoin.")
