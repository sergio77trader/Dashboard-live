import streamlit as st
import requests
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD

# -------------------------
# CONFIG
# -------------------------
TIMEFRAME = "1hour"
LIMIT = 120
BATCH_SIZE = 50

# -------------------------
# KUCOIN API
# -------------------------
BASE_URL = "https://api.kucoin.com"

def get_symbols():
    url = f"{BASE_URL}/api/v1/symbols"
    r = requests.get(url).json()
    return [s["symbol"] for s in r["data"] if s["quoteCurrency"] == "USDT"]

def get_klines(symbol):
    url = f"{BASE_URL}/api/v1/market/candles"
    params = {
        "symbol": symbol,
        "type": TIMEFRAME
    }
    r = requests.get(url, params=params).json()
    data = r.get("data", [])[:LIMIT]
    if not data:
        return None

    df = pd.DataFrame(
        data,
        columns=[
            "time","open","close","high","low","volume","turnover"
        ]
    )
    df = df.astype(float)
    df = df.iloc[::-1].reset_index(drop=True)
    return df

# -------------------------
# HEIKIN ASHI
# -------------------------
def heikin_ashi(df):
    ha = df.copy()
    ha["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

    ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha["ha_close"].iloc[i-1]) / 2)

    ha["ha_open"] = ha_open
    return ha

# -------------------------
# INDICATORS + SEMAFORO
# -------------------------
def analyze(df):
    # RSI
    rsi2 = RSIIndicator(df["close"], window=2).rsi().rolling(2).mean()
    rsi4 = RSIIndicator(df["close"], window=4).rsi().rolling(4).mean()

    # MACD
    macd = MACD(df["close"])
    hist = macd.macd_diff()

    # Volume
    vol_sma = df["volume"].rolling(20).mean()

    # Heikin Ashi
    ha = heikin_ashi(df)
    ha_body = abs(ha["ha_close"] - ha["ha_open"])
    ha_body_sma = ha_body.rolling(20).mean()

    i = -1  # última vela

    score = 0

    # RSI aceleración
    if rsi2.iloc[i] > rsi2.iloc[i-1]:
        score += 1
    else:
        score -= 1

    if rsi4.iloc[i] > rsi4.iloc[i-1]:
        score += 1
    else:
        score -= 1

    # MACD Histogram
    if hist.iloc[i] > hist.iloc[i-1]:
        score += 2
    else:
        score -= 2

    # Heikin Ashi
    if ha["ha_close"].iloc[i] > ha["ha_open"].iloc[i]:
        score += 1
    else:
        score -= 1

    # Volumen
    if df["volume"].iloc[i] > vol_sma.iloc[i]:
        score += 1
    else:
        score -= 1

    # Semáforo
    if score >= 4:
        semaforo = "🟢"
    elif score >= 1:
        semaforo = "🟡"
    else:
        semaforo = "🔴"

    # Money Inflow Score
    vol_ratio = df["volume"].iloc[i] / vol_sma.iloc[i]
    body_ratio = ha_body.iloc[i] / ha_body_sma.iloc[i]
    macd_strength = abs(hist.iloc[i] - hist.iloc[i-1])

    mis = vol_ratio * body_ratio * (1 + macd_strength)

    return {
        "RSI2": round(rsi2.iloc[i], 2),
        "RSI4": round(rsi4.iloc[i], 2),
        "MACD_hist": round(hist.iloc[i], 4),
        "Score": score,
        "Semaforo": semaforo,
        "Vol_Ratio": round(vol_ratio, 2),
        "MIS": round(mis, 2)
    }

# -------------------------
# STREAMLIT APP
# -------------------------
st.set_page_config(layout="wide")
st.title("🚦 KuCoin Money Inflow Scanner (1H)")

symbols = get_symbols()

run = st.button("🚀 Analizar mercado")

if run:
    results = []
    total_batches = len(symbols) // BATCH_SIZE + 1

    progress = st.progress(0)
    status = st.empty()

    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        status.text(f"Analizando lote {batch_num} / {total_batches}")

        for sym in batch:
            try:
                df = get_klines(sym)
                if df is None or len(df) < 50:
                    continue

                data = analyze(df)

                if data["Semaforo"] != "🔴":
                    results.append({
                        "Symbol": sym,
                        **data
                    })

            except:
                continue

        progress.progress(batch_num / total_batches)

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("MIS", ascending=False)

    st.subheader("🔥 Ranking – Dónde entra MÁS dinero ahora")
    st.dataframe(df_results, use_container_width=True)
