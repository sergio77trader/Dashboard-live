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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V27.0 SLY-PRO")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {"1m":"1m", "5m":"5m", "15m":"15m", "30m":"30m", "1H":"1h", "4H":"4h", "1D":"1d"}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_pairs(min_volume=50000):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume]
        return valid
    except: return []

# ─────────────────────────────────────────────
# NÚCLEO LÓGICO SLY (TRADUCCIÓN LITERAL PINE)
# ─────────────────────────────────────────────
def run_sly_engine(df, use_ema=True, use_zero=False):
    # 1. Preparar Indicadores
    ema200 = ta.ema(df["close"], length=200)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    hist = macd["MACDh_12_26_9"]
    macd_line = macd["MACD_12_26_9"]
    signal_line = macd["MACDs_12_26_9"]
    
    # 2. Heikin Ashi Recursivo
    ha_open = np.zeros(len(df))
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    # Inicialización de haOpen (na(haOpen[1]) ? (open + close) / 2)
    ha_open[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # 3. Máquina de Estados
    estado = 0
    entry_time = None
    
    # Empezamos el loop desde que EMA200 es válida (índice 199)
    for i in range(1, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        c = df["close"].iloc[i]
        e200 = ema200.iloc[i]
        
        # Saltamos si no hay data de indicadores (Warm-up)
        if np.isnan(e200) or np.isnan(h): continue

        # A. Salidas Dinámicas
        if estado == 1 and h < h_prev:
            estado = 0
        if estado == -1 and h > h_prev:
            estado = 0
            
        # B. Entradas (Solo si estamos en estado 0)
        if estado == 0:
            f_ema_long = (c > e200) if use_ema else True
            f_ema_short = (c < e200) if use_ema else True
            f_zero_long = (h < 0) if use_zero else True
            f_zero_short = (h > 0) if use_zero else True
            
            long_cond = (ha_color[i] == 1) and (h > h_prev) and f_ema_long and f_zero_long
            short_cond = (ha_color[i] == -1) and (h < h_prev) and f_ema_short and f_zero_short
            
            if long_cond:
                estado = 1
                entry_time = df["dt"].iloc[i]
            elif short_cond:
                estado = -1
                entry_time = df["dt"].iloc[i]
    
    return estado, entry_time, macd_line.iloc[-1], signal_line.iloc[-1], h.iloc[-1] if hasattr(h, 'iloc') else h

# ─────────────────────────────────────────────
# ANÁLISIS POR ACTIVO
# ─────────────────────────────────────────────
def analyze_ticker(symbol, tf_code, exchange, current_price, utc_offset=-3):
    try:
        # Necesitamos data suficiente para EMA200
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=400)
        if len(ohlcv) < 205: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        
        state, e_time, m_line, s_line, h_last = run_sly_engine(df)
        
        txt_sig = "FUERA ⚪"
        if state == 1: txt_sig = "LONG 🟢"
        elif state == -1: txt_sig = "SHORT 🔴"
        
        sig_time = (e_time + pd.Timedelta(hours=utc_offset)).strftime("%H:%M") if e_time else "--:--"
        
        # Info MACD para las otras columnas
        m0 = "SOBRE 0" if m_line > 0 else "BAJO 0"
        h_dir = "ALCISTA" if h_last > 0 else "BAJISTA" # Simplificado para dirección

        return {
            "signal": txt_sig,
            "signal_time": sig_time,
            "m0": m0,
            "h_dir": h_dir,
            "cross": "--:--" # Opcional: implementar cruce si se requiere
        }
    except: return None

# ─────────────────────────────────────────────
# LOGICA DE ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets, utc_h):
    ex = get_exchange()
    results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        clean = sym.split(":")[0].replace("/USDT", "")
        prog.progress((idx+1)/len(targets), text=f"Sincronizando {clean}...")
        try:
            p = ex.fetch_ticker(sym)["last"]
            row = {"Activo": clean, "Precio": f"{p:,.4f}"}
            for label, tf in TIMEFRAMES.items():
                res = analyze_ticker(sym, tf, ex, p, utc_h)
                if res:
                    row[f"{label} H.A./MACD"] = res["signal"]
                    row[f"{label} Hora Señal"] = res["signal_time"]
                    row[f"{label} MACD 0"] = res["m0"]
                    row[f"{label} Hist."] = res["h_dir"]
                else:
                    for c in ["H.A./MACD", "Hora Señal", "MACD 0", "Hist."]: row[f"{label} {c}"] = "-"
            
            # Veredicto SLY
            l_cnt = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
            s_cnt = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
            row["VEREDICTO"] = "🔥 COMPRA" if l_cnt >= 4 else "🩸 VENTA" if s_cnt >= 4 else "⚖️ RANGO"
            row["ESTRATEGIA"] = "CONFLUENCIA MTF" if (l_cnt >= 4 or s_cnt >= 4) else "SIN TENDENCIA"
            
            results.append(row)
            time.sleep(0.1)
        except: continue
    prog.empty()
    
    # Actualizar Session State
    current_data = {item["Activo"]: item for item in st.session_state["sniper_results"]}
    for item in results: current_data[item["Activo"]] = item
    return list(current_data.values())

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V27.0 (SLY CLONE)")

with st.sidebar:
    st.header("Terminal de Control")
    utc_h = st.number_input("Diferencia Horaria", value=-3)
    all_sym = get_active_pairs()
    
    if all_sym:
        st.success(f"Mercado: {len(all_sym)} activos")
        batch_size = st.selectbox("Tamaño de Lote", [20, 50, 100], index=1)
        batches = [all_sym[i:i+batch_size] for i in range(0, len(all_sym), batch_size)]
        sel = st.selectbox("Seleccionar Lote", range(len(batches)))
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["sniper_results"] = scan_batch(batches[sel], utc_h)
            
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# ESTILOS
def style_df(df):
    def apply_color(val):
        v = str(val).upper()
        if "LONG" in v or "COMPRA" in v or "SOBRE" in v or "ALCISTA" in v:
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in v or "VENTA" in v or "BAJO" in v or "BAJISTA" in v:
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        return ''
    return df.style.applymap(apply_color)

if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df_f.columns]
    others = [c for c in df_f.columns if c not in valid]
    st.dataframe(style_df(df_f[valid + others]), use_container_width=True, height=800)
