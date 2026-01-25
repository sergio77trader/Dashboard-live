import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V25.3")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { 
        border: 2px solid #2962FF !important; 
        border-radius: 8px !important;
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m":"1m", "5m":"5m", "15m":"15m",
    "30m":"30m", "1H":"1h", "4H":"4h", "1D":"1d"
}

# ─────────────────────────────────────────────
# DOCUMENTACIÓN TÉCNICA DETALLADA (EL MANUAL)
# ─────────────────────────────────────────────
with st.expander("📘 MANUAL OPERATIVO: ESPECIFICACIONES DE COLUMNAS"):
    st.info("Referencia exacta de las métricas y confluencias utilizadas por el motor Sniper.")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("""
        ### 🎯 LÓGICA DE VEREDICTOS
        *   **VEREDICTO:** La instrucción final ejecutiva.
            *   🔥 **COMPRA/VENTA FUERTE:** Se dispara cuando hay 5 o más columnas de tipo **[TF] H.A./MACD** con la misma señal (LONG o SHORT) y están alineadas con la tendencia de la columna **1D MACD 0**.
            *   💎 **GIRO/REBOTE:** Se dispara cuando las columnas **1m H.A./MACD**, **5m H.A./MACD** y **15m H.A./MACD** están todas en **LONG**, pero la columna **1D MACD 0** marca **BAJO 0**. (Detección de suelo).
            *   📉 **RETROCESO:** Se dispara cuando **1m, 5m y 15m H.A./MACD** están en **SHORT**, pero el sesgo estructural en **1D MACD 0** es **SOBRE 0**.
        *   **ESTRATEGIA:** El nombre técnico de la fase detectada (ej: MTF BULLISH SYNC).
        *   **MACD REC.:** Analiza la dirección del momentum en las columnas **15m Hist.**, **1H Hist.** y **4H Hist.**. Si la mayoría están en **SUBIENDO**, marca Momentum Alcista.
        """)
        
    with col_m2:
        st.markdown("""
        ### 📊 REFERENCIA DE COLUMNAS [TF]
        *   **[TF] H.A./MACD:** Indica el estado del precio. Combina la vela Heikin Ashi y el Histograma MACD de esa temporalidad. Incluye el RSI de esa misma vela como filtro.
        *   **[TF] Hora Señal:** Muestra la hora exacta en la que la columna **[TF] H.A./MACD** cambió por última vez de estado.
        *   **[TF] MACD 0:** Muestra si la línea MACD está **SOBRE 0** (alcista) o **BAJO 0** (bajista) en esa temporalidad específica.
        *   **[TF] Hist.:** Indica si la fuerza del movimiento está **SUBIENDO** o **BAJANDO** comparando la barra actual contra la anterior en esa temporalidad.
        *   **[TF] Cruce MACD:** Hora exacta en la que la línea MACD y la línea de Señal se cruzaron en esa temporalidad.
        """)

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})
    ex.load_markets()
    return ex

@st.cache_data(ttl=300)
def get_active_pairs(min_volume=100000):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        macd = ta.macd(df["close"])
        df["Hist"], df["MACD"], df["Signal"] = macd["MACDh_12_26_9"], macd["MACD_12_26_9"], macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        position = "NEUTRO"
        last_date = df["dt"].iloc[-1]
        for i in range(1, len(df)):
            hist, prev_hist = df["Hist"].iloc[i], df["Hist"].iloc[i - 1]
            ha_color, date = df["HA_Color"].iloc[i], df["dt"].iloc[i]
            if position == "LONG" and hist < prev_hist: position = "NEUTRO"
            elif position == "SHORT" and hist > prev_hist: position = "NEUTRO"
            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist: position, last_date = "LONG", date
                elif ha_color == -1 and hist < prev_hist: position, last_date = "SHORT", date

        icon = "🟢" if position == "LONG" else "🔴" if position == "SHORT" else "⚪"
        rsi_val = round(df["RSI"].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"]]
        cross_time = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "signal": f"{icon} {position} | {rsi_state}",
            "signal_time": (last_date - pd.Timedelta(hours=3)).strftime("%H:%M"),
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h_dir": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "cross_time": cross_time
        }
    except: return None

def get_verdict(row):
    # 'bulls' y 'bears' cuentan las columnas "[TF] H.A./MACD"
    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
    # 'bias_1d' lee específicamente la columna "1D MACD 0"
    bias_1d = str(row.get("1D MACD 0", ""))
    
    # Micro-confluencia basada en las columnas 1m, 5m y 15m H.A./MACD
    micro_bull = "LONG" in str(row.get("1m H.A./MACD","")) and "LONG" in str(row.get("5m H.A./MACD","")) and "LONG" in str(row.get("15m H.A./MACD",""))
    micro_bear = "SHORT" in str(row.get("1m H.A./MACD","")) and "SHORT" in str(row.get("5m H.A./MACD","")) and "SHORT" in str(row.get("15m H.A./MACD",""))

    if bulls >= 5 and "SOBRE 0" in bias_1d: return "🔥 COMPRA FUERTE", "MTF BULLISH SYNC"
    if bears >= 5 and "BAJO 0" in bias_1d: return "🩸 VENTA FUERTE", "MTF BEARISH SYNC"
    if micro_bull and "BAJO 0" in bias_1d: return "💎 GIRO/REBOTE", "FAST RECOVERY"
    if micro_bear and "SOBRE 0" in bias_1d: return "📉 RETROCESO", "CORRECTION START"
    return "⚖️ RANGO", "NO TREND"

def get_macd_recommendation(row):
    # Analiza específicamente las columnas de histograma de 15m, 1H y 4H
    subiendo = sum(1 for tf in ["15m", "1H", "4H"] if "SUBIENDO" in str(row.get(f"{tf} Hist.", "")))
    if subiendo >= 2: return "📈 MOMENTUM ALCISTA"
    if subiendo <= 1: return "📉 MOMENTUM BAJISTA"
    return "Neutral"

# ─────────────────────────────────────────────
# PROCESAMIENTO Y UI
# ─────────────────────────────────────────────
def scan_batch(targets, accumulate=True):
    ex = get_exchange()
    new_results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        clean = sym.split(":")[0].replace("/USDT", "")
        prog.progress((idx+1)/len(targets), text=f"Analizando {clean}...")
        try:
            p = ex.fetch_ticker(sym)["last"]
            row = {"Activo": clean, "Precio": f"{p:,.4f}"}
            for label, tf in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf, ex, p)
                if res:
                    row[f"{label} H.A./MACD"] = res["signal"]
                    row[f"{label} Hora Señal"] = res["signal_time"]
                    row[f"{label} MACD 0"] = res["m0"]
                    row[f"{label} Hist."] = res["h_dir"]
                    row[f"{label} Cruce MACD"] = res["cross_time"]
                else:
                    for c in ["H.A./MACD","Hora Señal","MACD 0","Hist.","Cruce MACD"]: row[f"{label} {c}"] = "-"
            row["VEREDICTO"], row["ESTRATEGIA"] = get_verdict(row)
            row["MACD REC."] = get_macd_recommendation(row)
            new_results.append(row)
            time.sleep(0.05)
        except: continue
    prog.empty()
    if accumulate:
        current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in new_results: current[r["Activo"]] = r
        return list(current.values())
    return new_results

def style_matrix(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA", "ALCISTA"]):
            return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA", "BAJISTA"]):
            return 'background-color: #f8d7da; color: #721c24;'
        if "GIRO" in v: return 'background-color: #fff3cd; color: #856404;'
        return ''
    return df.style.applymap(apply_color)

with st.sidebar:
    st.header("Radar Control")
    all_sym = get_active_pairs(min_volume=0)
    if all_sym:
        b_size = st.selectbox("Batch", [20, 50, 100], index=1)
        batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
        sel = st.selectbox("Lote", range(len(batches)))
        accumulate = st.checkbox("Acumular", value=True)
        if st.button("🚀 INICIAR ESCANEO", type="primary"):
            st.session_state["sniper_results"] = scan_batch(batches[sel], accumulate)
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    cols = ["Activo", "VEREDICTO", "ESTRATEGIA", "MACD REC.", "Precio"]
    remaining = [c for c in df.columns if c not in cols]
    st.dataframe(style_matrix(df[cols + remaining]), use_container_width=True, height=800)
else:
    st.info("👈 Presione INICIAR ESCANEO.")
