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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V15.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {"1m":"1m", "5m":"5m", "15m":"15m", "30m":"30m", "1H":"1h", "4H":"4h", "1D":"1d"}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 1000000]
    except: return []

def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

# ─────────────────────────────────────────────
# ANÁLISIS DE FASES (PULLBACKS & MOMENTUM)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- LÓGICA DE FASES SNIPER ---
        hist_val = last["Hist"]
        hist_prev = prev["Hist"]
        ha_color = last["HA_Color"]
        
        phase = "NEUTRO"
        icon = "⚪"
        
        # Bullish Logic
        if ha_color == 1 and hist_val > hist_prev:
            if hist_val < 0:
                phase = "PULLBACK ALCISTA" # Hist subiendo pero sigue abajo de 0
                icon = "🔵"
            else:
                phase = "MOMENTUM BULL" # Hist subiendo y ya sobre 0
                icon = "🟢"
        
        # Bearish Logic
        elif ha_color == -1 and hist_val < hist_prev:
            if hist_val > 0:
                phase = "PULLBACK BAJISTA" # Hist bajando pero sigue arriba de 0
                icon = "🟠"
            else:
                phase = "MOMENTUM BEAR" # Hist bajando y ya bajo 0
                icon = "🔴"

        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "main": f"{icon} {phase} | {rsi_state} ({rsi_val})",
            "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
            "h_dir": "Alcista" if hist_val > hist_prev else "Bajista",
            "cross": last_cross
        }
    except: return None

# ─────────────────────────────────────────────
# LÓGICA DE VEREDICTO
# ─────────────────────────────────────────────
def get_verdict(row):
    # Contar confluencias
    bull_signals = sum(1 for tf in TIMEFRAMES if "ALCISTA" in str(row.get(f"{tf} Sniper","")) or "BULL" in str(row.get(f"{tf} Sniper","")))
    bear_signals = sum(1 for tf in TIMEFRAMES if "BAJISTA" in str(row.get(f"{tf} Sniper","")) or "BEAR" in str(row.get(f"{tf} Sniper","")))
    
    # 1D Bias
    bias_1d = str(row.get("1D MACD 0", ""))
    
    if bull_signals >= 5 and "SOBRE 0" in bias_1d: return "🔥 COMPRA FUERTE", "TENDENCIA + MOMENTUM"
    if bear_signals >= 5 and "BAJO 0" in bias_1d: return "🩸 VENTA FUERTE", "TENDENCIA + MOMENTUM"
    if "PULLBACK ALCISTA" in str(row.get("1m Sniper", "")): return "💎 ENTRADA TEMPRANA", "POSIBLE GIRO"
    
    return "⚖️ RANGO / ESPERAR", "SIN CONFLUENCIA"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        clean = sym.split(":")[0].replace("/USDT", "")
        prog.progress((idx+1)/len(targets), text=f"Analizando {clean}")
        try:
            p = ex.fetch_ticker(sym)["last"]
            row = {"Activo": clean, "Precio": f"{p:,.4f}"}
            for label, tf in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf, ex, p)
                if res:
                    row[f"{label} Sniper"] = res["main"]
                    row[f"{label} MACD 0"] = res["m0"]
                    row[f"{label} Hist."] = res["h_dir"]
                    row[f"{label} Cruce"] = res["cross"]
                else:
                    for c in ["Sniper", "MACD 0", "Hist.", "Cruce"]: row[f"{label} {c}"] = "-"
            v, e = get_verdict(row)
            row["VEREDICTO"] = v
            row["ESTRATEGIA"] = e
            results.append(row)
            time.sleep(0.05)
        except: continue
    prog.empty()
    return results

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V15.0")
with st.sidebar:
    st.header("Configuración")
    all_sym = get_active_pairs()
    if all_sym:
        b_size = st.selectbox("Lote", [10, 20, 30], index=0)
        batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
        sel = st.selectbox("Lote", range(len(batches)))
        if st.button("🚀 ESCANEAR", type="primary"):
            st.session_state["sniper_results"] = scan_batch(batches[sel])
    if st.button("Limpiar"):
        st.session_state["sniper_results"] = []
        st.rerun()

def style_df(df):
    def color(val):
        v = str(val).upper()
        if "MOMENTUM BULL" in v or "SOBRE 0" in v or "COMPRA" in v: return 'background-color: #d4edda; color: #155724;'
        if "MOMENTUM BEAR" in v or "BAJO 0" in v or "VENTA" in v: return 'background-color: #f8d7da; color: #721c24;'
        if "PULLBACK ALCISTA" in v: return 'background-color: #e3f2fd; color: #0d47a1;' # Azul suave para giros
        if "PULLBACK BAJISTA" in v: return 'background-color: #fff3e0; color: #e65100;' # Naranja suave
        return ''
    return df.style.applymap(color)

if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df.columns]
    others = [c for c in df.columns if c not in valid]
    st.dataframe(style_df(df[valid + others]), use_container_width=True, height=800)
