import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
st.set_page_config(page_title="KuCoin RSI Momentum 1H", layout="wide")
st.title("📊 KuCoin | RSI Multi + MACD Histogram + Heikin Ashi (1H)")

RSI_LENGTHS = [2, 4, 6, 8, 12, 24, 84, 168]

# ─────────────────────────────
# DATA ENGINE (IGUAL A TU SCRIPT)
# ─────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoin({"enableRateLimit": True})
    ex.load_markets()
    return ex

@st.cache_data(ttl=300)
def get_symbols():
    ex = get_exchange()
    tickers = ex.fetch_tickers()
    return [s for s in tickers if s.endswith("/USDT")]

# ─────────────────────────────
# HEIKIN ASHI
# ─────────────────────────────
def heikin_ashi(df):
    ha = df.copy()
    ha["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha["HA_Close"].iloc[i-1]) / 2)
    ha["HA_Open"] = ha_open
    ha["HA_Color"] = np.where(ha["HA_Close"] > ha["HA_Open"], "GREEN", "RED")
    return ha

# ─────────────────────────────
# ANALISIS 1H
# ─────────────────────────────
def analyze(symbol):
    ex = get_exchange()
    ohlcv = ex.fetch_ohlcv(symbol, timeframe="1h", limit=200)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","vol"])

    # RSI multi (length = smoothing)
    for l in RSI_LENGTHS:
        rsi = ta.rsi(df["close"], length=l)
        df[f"RSI_{l}"] = rsi.rolling(l).mean()

    # MACD Histogram
    macd = ta.macd(df["close"])
    df["HIST"] = macd["MACDh_12_26_9"]

    # Heikin Ashi
    df = heikin_ashi(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # RSI aceleración (rápidos)
    rsi_up = last["RSI_2"] > prev["RSI_2"] and last["RSI_4"] > prev["RSI_4"]
    rsi_down = last["RSI_2"] < prev["RSI_2"] and last["RSI_4"] < prev["RSI_4"]

    # MACD hist
    macd_up = last["HIST"] > prev["HIST"]
    macd_down = last["HIST"] < prev["HIST"]

    # Heikin Ashi
    ha_green = last["HA_Color"] == "GREEN"
    ha_red = last["HA_Color"] == "RED"

    if rsi_up and macd_up and ha_green:
        signal = "🟢 COMPRA"
    elif rsi_down and macd_down and ha_red:
        signal = "🔴 VENTA"
    else:
        signal = "⚪ NEUTRO"

    return {
        "Precio": round(last["close"], 4),
        "RSI2": round(last["RSI_2"],1),
        "RSI4": round(last["RSI_4"],1),
        "MACD_Hist": round(last["HIST"],5),
        "HA": last["HA_Color"],
        "Señal": signal
    }

# ─────────────────────────────
# UI
# ─────────────────────────────
symbols = get_symbols()
selected = st.multiselect("Seleccionar criptos:", symbols, default=symbols[:5])

if st.button("🚀 ANALIZAR"):
    rows = []
    for s in selected:
        try:
            r = analyze(s)
            r["Activo"] = s.replace("/USDT","")
            rows.append(r)
        except:
            pass

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
