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
st.set_page_config(layout="wide", page_title="SystemaTrader: HA + MACD")

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# ─────────────────────────────────────────────
# TEMPORALIDADES
# ─────────────────────────────────────────────
TIMEFRAMES = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d"
}

# ─────────────────────────────────────────────
# EXCHANGE
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({"enableRateLimit": True})
    ex.load_markets()
    return ex

@st.cache_data(ttl=3600)
def get_active_pairs():
    ex = get_exchange()
    tickers = ex.fetch_tickers()
    data = []
    for s, t in tickers.items():
        if "/USDT:USDT" in s and t.get("quoteVolume"):
            data.append((s, t["quoteVolume"]))
    return [x[0] for x in sorted(data, key=lambda x: x[1], reverse=True)]

# ─────────────────────────────────────────────
# HEIKIN ASHI
# ─────────────────────────────────────────────
def heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df.open + df.high + df.low + df.close) / 4
    ha_open = [df.open.iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + df.HA_Close.iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df.HA_Close > df.HA_Open, 1, -1)
    return df

# ─────────────────────────────────────────────
# ANÁLISIS TF
# ─────────────────────────────────────────────
def analyze_tf(symbol, tf, exchange, price):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=150)
    if len(ohlcv) < 60:
        return None

    ohlcv[-1][4] = price
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","vol"])
    df["dt"] = pd.to_datetime(df.time, unit="ms")

    macd = ta.macd(df.close)
    df["MACD"] = macd["MACD_12_26_9"]
    df["SIGNAL"] = macd["MACDs_12_26_9"]
    df["HIST"] = macd["MACDh_12_26_9"]
    df["RSI"] = ta.rsi(df.close, 14)

    df = heikin_ashi(df)

    hist_dir = "Alcista" if df.HIST.iloc[-1] > df.HIST.iloc[-2] else "Bajista"

    last_cross = "-"
    for i in range(len(df)-1, 1, -1):
        prev = df.MACD.iloc[i-1] - df.SIGNAL.iloc[i-1]
        curr = df.MACD.iloc[i] - df.SIGNAL.iloc[i]
        if prev <= 0 < curr or prev >= 0 > curr:
            last_cross = (df.dt.iloc[i] - pd.Timedelta(hours=3)).strftime("%H:%M")
            break

    position = "NEUTRO"
    for i in range(1, len(df)):
        if df.HA_Color.iloc[i] == 1 and df.HIST.iloc[i] > df.HIST.iloc[i-1]:
            position = "LONG"
        elif df.HA_Color.iloc[i] == -1 and df.HIST.iloc[i] < df.HIST.iloc[i-1]:
            position = "SHORT"

    rsi = round(df.RSI.iloc[-1], 1)
    rsi_state = "RSI↑" if rsi > 55 else "RSI↓" if rsi < 45 else "RSI="

    return position, hist_dir, last_cross, rsi_state, rsi

# ─────────────────────────────────────────────
# 🔧 FUNCIÓN QUE FALTABA (ERROR CORREGIDO)
# ─────────────────────────────────────────────
def get_recommendation(row):
    longs = sum("LONG" in str(row.get(f"{tf} HA-MACD","")) for tf in TIMEFRAMES)
    shorts = sum("SHORT" in str(row.get(f"{tf} HA-MACD","")) for tf in TIMEFRAMES)

    if longs >= 5:
        return "📈 COMPRA FUERTE"
    if shorts >= 5:
        return "📉 VENTA FUERTE"
    return "⏸ NEUTRO"

def macd_recommendation(row):
    bulls = sum("Alcista" in str(row.get(f"MACD HIST {tf}","")) for tf in TIMEFRAMES)
    bears = sum("Bajista" in str(row.get(f"MACD HIST {tf}","")) for tf in TIMEFRAMES)

    if bulls >= 5:
        return "MACD ALCISTA"
    if bears >= 5:
        return "MACD BAJISTA"
    return "MACD MIXTO"

def final_verdict(row):
    if "COMPRA FUERTE" in row["Estrategia"] and "ALCISTA" in row["Recomendación MACD"]:
        return "🚀 LONG"
    if "VENTA FUERTE" in row["Estrategia"] and "BAJISTA" in row["Recomendación MACD"]:
        return "💣 SHORT"
    return "⏳ ESPERAR"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(symbols):
    ex = get_exchange()
    rows = []

    for sym in symbols:
        price = ex.fetch_ticker(sym)["last"]
        row = {"Activo": sym.replace("/USDT:USDT","")}

        for lbl, tf in TIMEFRAMES.items():
            res = analyze_tf(sym, tf, ex, price)
            if res:
                pos, hist, cross, rsi_state, rsi = res
                icon = "🟢" if pos=="LONG" else "🔴" if pos=="SHORT" else "⚪"
                row[f"{lbl} HA-MACD"] = f"{icon} {pos} | {rsi_state} ({rsi})"
                row[f"MACD HIST {lbl}"] = hist
                row[f"CRUCE HORA {lbl}"] = cross
            else:
                row[f"{lbl} HA-MACD"] = "-"
                row[f"MACD HIST {lbl}"] = "-"
                row[f"CRUCE HORA {lbl}"] = "-"

        row["Estrategia"] = get_recommendation(row)
        row["Recomendación MACD"] = macd_recommendation(row)
        row["VEREDICTO"] = final_verdict(row)

        rows.append(row)

    return rows

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("📊 HA + MACD Dashboard")

symbols = get_active_pairs()

if st.button("ESCANEAR"):
    st.session_state["sniper_results"] = scan_batch(symbols[:20])

if st.session_state["sniper_results"]:
    st.dataframe(pd.DataFrame(st.session_state["sniper_results"]), use_container_width=True)
