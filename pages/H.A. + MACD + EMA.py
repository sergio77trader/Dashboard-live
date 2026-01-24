import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SystemaTrader: HA + MACD Matrix")

st.markdown("""
<style>
    .stDataFrame { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

if 'final_results' not in st.session_state:
    st.session_state['final_results'] = []

TIMEFRAMES = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
}

# ─────────────────────────────────────────────
# EXCHANGE (UNA SOLA VEZ)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.binance({
        "enableRateLimit": True,
        "timeout": 30000,
        "options": {"defaultType": "future"}
    })
    ex.load_markets()
    return ex

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
def get_data(symbol, tf, limit=200):
    try:
        ex = get_exchange()
        ohlcv = ex.fetch_ohlcv(symbol, tf, limit=limit)
        if not ohlcv or len(ohlcv) < 50:
            return None

        df = pd.DataFrame(
            ohlcv,
            columns=["time","open","high","low","close","volume"]
        )
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        return df

    except:
        return None

# ─────────────────────────────────────────────
# HEIKIN ASHI
# ─────────────────────────────────────────────
def heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

# ─────────────────────────────────────────────
# ANALISIS POR TF
# ─────────────────────────────────────────────
def analyze_tf(symbol, tf):
    df = get_data(symbol, tf)
    if df is None:
        return None

    macd = ta.macd(df["close"])
    df["MACD"] = macd["MACD_12_26_9"]
    df["SIGNAL"] = macd["MACDs_12_26_9"]
    df["HIST"] = macd["MACDh_12_26_9"]

    df["RSI"] = ta.rsi(df["close"], 14)
    df = heikin_ashi(df)

    # ── HA + HIST
    state = "NEUTRO"
    last_dt = df["dt"].iloc[-1]

    for i in range(1, len(df)):
        if df["HA_Color"].iloc[i] == 1 and df["HIST"].iloc[i] > df["HIST"].iloc[i-1]:
            state = "LONG"
            last_dt = df["dt"].iloc[i]
        elif df["HA_Color"].iloc[i] == -1 and df["HIST"].iloc[i] < df["HIST"].iloc[i-1]:
            state = "SHORT"
            last_dt = df["dt"].iloc[i]

    # RSI
    rsi_val = round(df["RSI"].iloc[-1], 1)
    rsi_txt = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

    # ── CRUCE MACD (ULTIMA VELA CERRADA)
    df["CROSS"] = np.where(df["MACD"] > df["SIGNAL"], 1, -1)
    cross = df["CROSS"].diff()

    cross_type = "-"
    cross_time = "-"

    if cross.iloc[-2] != 0:
        cross_type = "ALCISTA" if df["CROSS"].iloc[-2] == 1 else "BAJISTA"
        cross_time = (df["dt"].iloc[-2] - pd.Timedelta(hours=3)).strftime("%H:%M")

    return {
        "state": state,
        "hour": (last_dt - pd.Timedelta(hours=3)).strftime("%H:%M"),
        "rsi": f"{rsi_txt} ({rsi_val})",
        "cross": cross_type,
        "cross_time": cross_time
    }

# ─────────────────────────────────────────────
# SCAN
# ─────────────────────────────────────────────
def scan(symbols):
    rows = []
    for sym in symbols:
        row = {"Activo": sym.replace("USDT","")}
        for tf, code in TIMEFRAMES.items():
            r = analyze_tf(sym, code)
            if r:
                icon = "🟢" if r["state"] == "LONG" else "🔴" if r["state"] == "SHORT" else "⚪"
                row[f"{tf} HA-MACD"] = f"{icon} {r['state']} | {r['rsi']}"
                row[f"{tf} ALERTA"] = r["hour"]
                row[f"{tf} CRUCE"] = r["cross"]
                row[f"{tf} HORA CRUCE"] = r["cross_time"]
            else:
                row[f"{tf} HA-MACD"] = "-"
                row[f"{tf} ALERTA"] = "-"
                row[f"{tf} CRUCE"] = "-"
                row[f"{tf} HORA CRUCE"] = "-"
        rows.append(row)
        time.sleep(0.1)
    return rows

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("📊 HA + MACD + RSI Matrix")

symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

if st.button("ESCANEAR"):
    st.session_state["final_results"] = scan(symbols)

if st.session_state["final_results"]:
    df = pd.DataFrame(st.session_state["final_results"])
    st.dataframe(df, use_container_width=True)
else:
    st.info("Presioná ESCANEAR")
