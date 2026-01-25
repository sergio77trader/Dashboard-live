import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | V36.0 PRECISION")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #2962FF; font-weight: 800; letter-spacing: -1px; }
    .stProgress > div > div > div > div { background-color: #00E676; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (CON RESILIENCIA)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        "enableRateLimit": True, 
        "timeout": 45000,
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
# NÚCLEO LÓGICO SLY (BUFFER DE ESTABILIZACIÓN)
# ─────────────────────────────────────────────
def run_sly_engine(df, use_ema):
    # 1. EMA 200 con Buffer de Estabilización
    # Para que una EMA sea precisa, necesita ~2.5 veces su longitud en datos previos
    ema_val = ta.ema(df['close'], length=200)
    
    # 2. MACD (12, 26, 9)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, None
    hist = macd['MACDh_12_26_9']

    # 3. Heikin Ashi Recursivo (Precisión Pine Script)
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # 4. Máquina de Estados (Loop barra a barra)
    estado = 0
    entry_time = None
    
    # Empezamos el análisis después de 200 velas (Warm-up completo)
    # Esto garantiza que la señal que veas sea con indicadores ESTABLES
    start_idx = 200 if len(df) > 200 else 34
    
    for i in range(start_idx, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        price = df['close'].iloc[i]
        
        # Validación de EMA
        e_v = ema_val.iloc[i] if (ema_val is not None and not pd.isna(ema_val.iloc[i])) else None
        
        prev_estado = estado

        # Salidas Dinámicas
        if estado == 1 and h < h_prev: estado = 0
        elif estado == -1 and h > h_prev: estado = 0
            
        # Entradas con Filtro EMA Sincronizado
        if estado == 0:
            f_ema_long = (price > e_v) if (use_ema and e_v) else True
            f_ema_short = (price < e_v) if (use_ema and e_v) else True
            
            if (ha_color[i] == 1) and (h > h_prev) and f_ema_long:
                estado = 1
            elif (ha_color[i] == -1) and (h < h_prev) and f_ema_short:
                estado = -1
        
        if estado != 0 and estado != prev_estado:
            entry_time = df['dt'].iloc[i]

    return estado, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR MTF (PROTOCOLO DE REINTENTOS)
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_h, use_ema):
    row = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        ohlcv = None
        # Intento 1: Máxima Precisión (450 velas)
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=450)
        except:
            # Intento 2: Modo Supervivencia (200 velas) si falla el primero
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
            except:
                ohlcv = None

        if not ohlcv or len(ohlcv) < 50:
            row[f"{label} Señal"] = "SIN DATA"
            row[f"{label} Horario"] = "-"
            continue
            
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        st_val, tm_val = run_sly_engine(df, use_ema)
        
        if st_val == 1:
            row[f"{label} Señal"] = "LONG 🟢"
            row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M") if tm_val else "Reciente"
        elif st_val == -1:
            row[f"{label} Señal"] = "SHORT 🔴"
            row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M") if tm_val else "Reciente"
        else:
            row[f"{label} Señal"] = "FUERA ⚪"
            row[f"{label} Horario"] = "-"
            
    return row

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SLY DASHBOARD | V36.0 PRECISION")

with st.sidebar:
    st.header("Parámetros")
    u_ema = st.checkbox("Filtro EMA 200 (Estructural)", value=True)
    utc_val = st.number_input("Zona Horaria (UTC)", value=-3)
    
    st.divider()
    all_pairs = get_active_pairs()
    if all_pairs:
        st.success(f"Mercado: {len(all_pairs)} activos")
        b_size = st.selectbox("Lote", [10, 20, 50], index=1)
        batches = [all_pairs[i:i+b_size] for i in range(0, len(all_pairs), b_size)]
        sel_batch = st.selectbox("Seleccionar Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
        
        if st.button("🚀 SINCRONIZAR", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx+1)/len(batches[sel_batch]), text=f"Procesando {sym}...")
                results.append(analyze_ticker(sym, ex, utc_val, u_ema))
                time.sleep(0.1) 
            st.session_state["sniper_results"] = results
            prog.empty()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# RENDERIZADO
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    def color_cells(val):
        if "LONG" in str(val): return 'background-color: #E8F5E9; color: #2E7D32; font-weight: bold'
        if "SHORT" in str(val): return 'background-color: #FFEBEE; color: #C62828; font-weight: bold'
        return ''

    st.dataframe(df_f.style.applymap(color_cells), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione SINCRONIZAR para obtener datos de alta fidelidad.")
