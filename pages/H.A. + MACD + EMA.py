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
def get_active_pairs(min_volume=100000):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
    except:
        return []

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
# ANÁLISIS TÉCNICO (MODIFICADO SOLO HA + MACD)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]

        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        phase = "NEUTRO"
        icon = "⚪"

        # 🟦 ALERTA ALCISTA (ROJO → VERDE + HIST ↓)
        if prev["HA_Color"] == -1 and last["HA_Color"] == 1 and last["Hist"] < prev["Hist"]:
            phase, icon = "PULLBACK ALCISTA", "🔵"

        # 🟢 CONFIRMACIÓN ALCISTA
        elif last["HA_Color"] == 1 and last["Hist"] > prev["Hist"]:
            phase, icon = "CONFIRMACION BULL", "🟢"

        # 🟧 ALERTA BAJISTA (VERDE → ROJO + HIST ↑)
        elif prev["HA_Color"] == 1 and last["HA_Color"] == -1 and last["Hist"] > prev["Hist"]:
            phase, icon = "PULLBACK BAJISTA", "🟠"

        # 🔴 CONFIRMACIÓN BAJISTA
        elif last["HA_Color"] == -1 and last["Hist"] < prev["Hist"]:
            phase, icon = "CONFIRMACION BEAR", "🔴"

        signal_time = (last["dt"] - pd.Timedelta(hours=3)).strftime("%H:%M")

        return {
            "signal": f"{icon} {phase}",
            "signal_time": signal_time,
            "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if last["Hist"] > prev["Hist"] else "BAJISTA",
            "cross_time": "--:--"
        }

    except:
        return None

# ─────────────────────────────────────────────
# EL RESTO DEL SCRIPT QUEDA EXACTAMENTE IGUAL
# (scan_batch, filtros, UI, render)
# ─────────────────────────────────────────────
