import streamlit as st
import pandas as pd
import numpy as np
import ccxt
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(page_title="KuCoin Momentum Scanner", layout="wide")
st.title("📈 KuCoin – RSI 2(2) + RSI 4(4) + MACD + Heikin Ashi (1H)")

# ---------------------------
# KUCOIN DATA
# ---------------------------
exchange = ccxt.kucoin()

symbol = st.selectbox("Par", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
limit = 200

ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=limit)
df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])
df["time"] = pd.to_datetime(df["time"], unit="ms")

# ---------------------------
# RSI + SMOOTHING
# ---------------------------
def rsi_smoothed(close, length):
    rsi = RSIIndicator(close, window=length).rsi()
    return rsi.rolling(length).mean()

df["rsi2"] = rsi_smoothed(df["close"], 2)
df["rsi4"] = rsi_smoothed(df["close"], 4)

# ---------------------------
# MACD HISTOGRAM
# ---------------------------
macd = MACD(df["close"])
df["macd_hist"] = macd.macd_diff()

# ---------------------------
# HEIKIN ASHI
# ---------------------------
df["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
df["ha_open"] = df["open"].copy()

for i in range(1, len(df)):
    df.loc[i, "ha_open"] = (df.loc[i-1, "ha_open"] + df.loc[i-1, "ha_close"]) / 2

df["ha_green"] = df["ha_close"] > df["ha_open"]

# ---------------------------
# SIGNAL LOGIC
# ---------------------------
last = df.iloc[-1]
prev = df.iloc[-2]

rsi_up = last["rsi2"] > prev["rsi2"] and last["rsi4"] > prev["rsi4"]
rsi_down = last["rsi2"] < prev["rsi2"] and last["rsi4"] < prev["rsi4"]

macd_up = last["macd_hist"] > prev["macd_hist"]
macd_down = last["macd_hist"] < prev["macd_hist"]

buy = rsi_up and macd_up and last["ha_green"]
sell = rsi_down and macd_down and not last["ha_green"]

# ---------------------------
# OUTPUT
# ---------------------------
col1, col2, col3 = st.columns(3)

col1.metric("RSI 2 (2)", round(last["rsi2"], 2))
col2.metric("RSI 4 (4)", round(last["rsi4"], 2))
col3.metric("MACD Hist", round(last["macd_hist"], 4))

st.subheader("📍 Señal")

if buy:
    st.success("🟢 COMPRA PERFECTA")
elif sell:
    st.error("🔴 VENTA PERFECTA")
else:
    st.info("⚪ SIN SEÑAL")

st.dataframe(df.tail(10))
