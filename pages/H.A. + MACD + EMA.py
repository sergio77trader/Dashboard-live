import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIG STREAMLIT
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SystemaTrader V24 - HA + MACD")

st.title("📊 SystemaTrader V24 — HA + MACD + Alertas")

# ─────────────────────────────────────────────
# EXCHANGE
# ─────────────────────────────────────────────
exchange = ccxt.binance({
    "enableRateLimit": True
})

# ─────────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────────
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
timeframes = {
    "15m": "15m",
    "1h": "1h",
    "4h": "4h"
}

# ─────────────────────────────────────────────
# HEIKIN ASHI
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = ha_close.copy()
    ha_open.iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2

    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

    ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)

    df["HA_Open"] = ha_open
    df["HA_Close"] = ha_close
    df["HA_High"] = ha_high
    df["HA_Low"] = ha_low
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

# ─────────────────────────────────────────────
# ANALISIS POR TF
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=120)
        if len(ohlcv) < 50:
            return None

        df = pd.DataFrame(
            ohlcv,
            columns=["time", "open", "high", "low", "close", "volume"]
        )
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        # MACD
        macd = ta.macd(df["close"])
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["Hist"] = macd["MACDh_12_26_9"]

        # RSI
        df["RSI"] = ta.rsi(df["close"], length=14)

        # HA
        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # LOGICA HA + HIST
        ha_green = last["HA_Color"] == 1
        ha_red = last["HA_Color"] == -1

        hist_up = last["Hist"] > prev["Hist"]
        hist_down = last["Hist"] < prev["Hist"]

        prev_long = prev["HA_Color"] == 1 and prev["Hist"] > df.iloc[-3]["Hist"]
        prev_short = prev["HA_Color"] == -1 and prev["Hist"] < df.iloc[-3]["Hist"]

        signal = "—"
        alert_time = "—"

        if ha_green and hist_up and not prev_long:
            signal = "🟢 LONG"
            alert_time = (last["dt"] - timedelta(hours=3)).strftime("%H:%M")

        elif ha_red and hist_down and not prev_short:
            signal = "🔴 SHORT"
            alert_time = (last["dt"] - timedelta(hours=3)).strftime("%H:%M")

        # RSI estado
        rsi_val = round(last["RSI"], 1)
        if rsi_val > 55:
            rsi_state = "RSI↑"
        elif rsi_val < 45:
            rsi_state = "RSI↓"
        else:
            rsi_state = "RSI="

        ha_macd_col = f"{signal} | {rsi_state} ({rsi_val})"

        return {
            "HA-MACD": ha_macd_col,
            "Alerta": alert_time
        }

    except Exception as e:
        st.write(f"Error {symbol} {tf}: {e}")
        return None

# ─────────────────────────────────────────────
# SCAN
# ─────────────────────────────────────────────
rows = []

for symbol in symbols:
    for tf_name, tf in timeframes.items():
        data = analyze_ticker_tf(symbol, tf)
        if data:
            rows.append({
                "Par": symbol,
                "TF": tf_name,
                "HA-MACD": data["HA-MACD"],
                "Alerta": data["Alerta"]
            })

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
df_result = pd.DataFrame(rows)

if df_result.empty:
    st.warning("Sin señales activas.")
else:
    st.dataframe(df_result, use_container_width=True)
