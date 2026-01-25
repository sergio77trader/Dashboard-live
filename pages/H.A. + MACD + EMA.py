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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V24.0")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m":"1m","5m":"5m","15m":"15m",
    "30m":"30m","1H":"1h","4H":"4h","1D":"1d"
}

# ─────────────────────────────────────────────
# EXCHANGE
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True})

@st.cache_data(ttl=300)
def get_active_pairs():
    ex = get_exchange()
    t = ex.fetch_tickers()
    return [s for s in t if "/USDT:USDT" in s]

# ─────────────────────────────────────────────
# HEIKIN ASHI
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

# ─────────────────────────────────────────────
# ANALISIS
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf, ex, price):
    ohlcv = ex.fetch_ohlcv(symbol, tf, limit=100)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","vol"])
    df["dt"] = pd.to_datetime(df["time"], unit="ms")
    df.iloc[-1,4] = price

    macd = ta.macd(df["close"])
    df["Hist"] = macd["MACDh_12_26_9"]
    df["MACD"] = macd["MACD_12_26_9"]
    df["Signal"] = macd["MACDs_12_26_9"]

    df = calculate_heikin_ashi(df)
    last, prev = df.iloc[-1], df.iloc[-2]

    phase, icon = "NEUTRO","⚪"
    if last["HA_Color"] == 1 and last["Hist"] > prev["Hist"]:
        phase, icon = ("CONFIRMACION BULL","🟢")
    elif last["HA_Color"] == -1 and last["Hist"] < prev["Hist"]:
        phase, icon = ("CONFIRMACION BEAR","🔴")

    df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
    crosses = df[df["cross"]]

    cross_time = (
        (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        if not crosses.empty else "--"
    )

    signal_time = (last["dt"] - pd.Timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

    return {
        "signal": f"{icon} {phase}",   # ← HA-MACD limpio
        "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
        "hist": "ALCISTA" if last["Hist"] > prev["Hist"] else "BAJISTA",
        "cross": cross_time,
        "time": signal_time            # ← hora visible
    }

# ─────────────────────────────────────────────
# SCAN
# ─────────────────────────────────────────────
def scan(symbols):
    ex = get_exchange()
    out = []
    for s in symbols:
        p = ex.fetch_ticker(s)["last"]
        row = {"Activo": s.replace("/USDT:USDT",""), "Precio": round(p,4)}
        for lbl,tf in TIMEFRAMES.items():
            r = analyze_ticker_tf(s, tf, ex, p)
            row[f"{lbl} H.A./MACD"] = r["signal"]
            row[f"{lbl} Hora Señal"] = r["time"]
            row[f"{lbl} MACD 0"] = r["m0"]
            row[f"{lbl} Hist."] = r["hist"]
            row[f"{lbl} Cruce MACD"] = r["cross"]
        out.append(row)
    return out

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("SYSTEMATRADER | SNIPER V24.0")

symbols = get_active_pairs()

if st.button("🚀 INICIAR ESCANEO"):
    st.session_state["sniper_results"] = scan(symbols[:20])

if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    st.dataframe(df, use_container_width=True)
else:
    st.info("Presione INICIAR ESCANEO")
