import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | V33.0 FIXED")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; padding-bottom: 10px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# Timeframes exactos para KuCoin
TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN (FORZADO)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({
        "enableRateLimit": True, 
        "timeout": 50000,
        "options": {"defaultType": "future"}
    })
    return ex

@st.cache_data(ttl=600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        # Filtramos solo activos con volumen real en USDT
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 10000]
    except: return []

# ─────────────────────────────────────────────
# LÓGICA SLY (CLON TRADINGVIEW)
# ─────────────────────────────────────────────
def run_sly_engine(df, use_ema, use_zero):
    # 1. Indicadores
    ema200 = ta.ema(df['close'], length=200)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, None
    hist = macd['MACDh_12_26_9']

    # 2. Heikin Ashi Exacto
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # 3. Máquina de Estados (Loop SLY)
    estado = 0
    entry_time = None
    
    # Empezamos desde donde hay MACD (vela 34 aprox)
    for i in range(1, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        price = df['close'].iloc[i]
        
        # Filtro EMA dinámico (Si no hay data para 200, se ignora el filtro para no dar S/D)
        e200 = ema200.iloc[i] if (ema200 is not None and i < len(ema200)) else None
        f_ema_long = (price > e200) if (use_ema and e200 is not None and not pd.isna(e200)) else True
        f_ema_short = (price < e200) if (use_ema and e200 is not None and not pd.isna(e200)) else True
        
        f_zero_long = (h < 0) if use_zero else True
        f_zero_short = (h > 0) if use_zero else True

        # Salidas
        if estado == 1 and h < h_prev: estado = 0
        elif estado == -1 and h > h_prev: estado = 0
            
        # Entradas
        if estado == 0:
            if (ha_color[i] == 1) and (h > h_prev) and f_ema_long and f_zero_long:
                estado = 1
                entry_time = df['dt'].iloc[i]
            elif (ha_color[i] == -1) and (h < h_prev) and f_ema_short and f_zero_short:
                estado = -1
                entry_time = df['dt'].iloc[i]
                
    return estado, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR ROBUSTO
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_h, use_ema, use_zero):
    row = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        try:
            # Solución definitiva al S/D: Calcular tiempo atrás para forzar datos
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=250)
            
            if not ohlcv or len(ohlcv) < 50:
                row[f"{label} Señal"] = "S/D"
                row[f"{label} Horario"] = "-"
                continue
                
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            
            st_val, tm_val = run_sly_engine(df, use_ema, use_zero)
            
            if st_val == 1:
                row[f"{label} Señal"] = "LONG 🟢"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M")
            elif st_val == -1:
                row[f"{label} Señal"] = "SHORT 🔴"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%H:%M")
            else:
                row[f"{label} Señal"] = "FUERA ⚪"
                row[f"{label} Horario"] = "-"
        except:
            row[f"{label} Señal"] = "Error API"
            row[f"{label} Horario"] = "-"
            
    return row

# ─────────────────────────────────────────────
# INTERFAZ Streamlit
# ─────────────────────────────────────────────
st.title("🎯 SLY DASHBOARD | V33.0 FIXED")

with st.sidebar:
    st.header("Configuración SLY")
    u_ema = st.checkbox("Filtro EMA 200", value=True)
    u_zero = st.checkbox("Filtro Cruce Cero", value=False)
    utc_val = st.number_input("Horario UTC (Arg = -3)", value=-3)
    
    st.divider()
    all_pairs = get_active_pairs()
    if all_pairs:
        st.success(f"Mercado: {len(all_pairs)} activos")
        b_size = st.selectbox("Batch Size", [10, 20, 50], index=1)
        batches = [all_pairs[i:i+b_size] for i in range(0, len(all_pairs), b_size)]
        sel_batch = st.selectbox("Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} pares)")
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx+1)/len(batches[sel_batch]), text=f"Escaneando {sym}...")
                results.append(analyze_ticker(sym, ex, utc_val, u_ema, u_zero))
                time.sleep(0.1) # Estabilidad
            st.session_state["sniper_results"] = results
            prog.empty()

    if st.button("Limpiar Pantalla"):
        st.session_state["sniper_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    def color_rows(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "FUERA" in str(val): return 'color: #9E9E9E;'
        return ''

    st.dataframe(df_final.style.applymap(color_rows), use_container_width=True, height=800)
else:
    st.info("👈 Selecciona un lote y presiona Escanear. Esta versión ignora el requisito de 200 velas si no hay historial para asegurar que veas datos.")
