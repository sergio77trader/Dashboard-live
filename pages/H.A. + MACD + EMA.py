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
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ Sniper Matrix")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 14px; }
.stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MEMORIA
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
# CONEXIÓN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({
        "enableRateLimit": True,
        "timeout": 30000
    })
    ex.load_markets()
    return ex

@st.cache_data(ttl=3600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []

        for s in tickers:
            if "/USDT:USDT" in s and tickers[s].get("quoteVolume"):
                valid.append({"symbol": s, "vol": tickers[s]["quoteVolume"]})

        return (
            pd.DataFrame(valid)
            .sort_values("vol", ascending=False)["symbol"]
            .tolist()
        )
    except:
        return []

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
# ANÁLISIS POR TF
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(
            ohlcv,
            columns=["time", "open", "high", "low", "close", "vol"]
        )
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["MACD"] = macd["MACD_12_26_9"]
        df["SIGNAL"] = macd["MACDs_12_26_9"]
        df["HIST"] = macd["MACDh_12_26_9"]

        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        # ─── MACD HIST dirección
        hist_dir = "↑" if df["HIST"].iloc[-1] > df["HIST"].iloc[-2] else "↓"

        # ─── Cruce MACD
        cross = "-"
        cross_time = "-"
        if df["MACD"].iloc[-2] < df["SIGNAL"].iloc[-2] and df["MACD"].iloc[-1] > df["SIGNAL"].iloc[-1]:
            cross = "BULL"
            cross_time = (df["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M")
        elif df["MACD"].iloc[-2] > df["SIGNAL"].iloc[-2] and df["MACD"].iloc[-1] < df["SIGNAL"].iloc[-1]:
            cross = "BEAR"
            cross_time = (df["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M")

        position = "NEUTRO"
        for i in range(1, len(df)):
            if df["HA_Color"].iloc[i] == 1 and df["HIST"].iloc[i] > df["HIST"].iloc[i-1]:
                position = "LONG"
            elif df["HA_Color"].iloc[i] == -1 and df["HIST"].iloc[i] < df["HIST"].iloc[i-1]:
                position = "SHORT"

        rsi_val = round(df["RSI"].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        return position, hist_dir, cross, cross_time, rsi_state, rsi_val

    except:
        return None

# ─────────────────────────────────────────────
# RECOMENDACIONES
# ─────────────────────────────────────────────
def macd_only_reco(hist, cross):
    if cross == "BULL" and hist == "↑":
        return "MACD COMPRA"
    if cross == "BEAR" and hist == "↓":
        return "MACD VENTA"
    return "MACD NEUTRO"

def full_reco(row):
    if "LONG" in row and "RSI↑" in row:
        return "🔥 COMPRA CONFIRMADA"
    if "SHORT" in row and "RSI↓" in row:
        return "🩸 VENTA CONFIRMADA"
    return "⚖️ ESPERAR"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0)

    for i, sym in enumerate(targets):
        prog.progress((i + 1) / len(targets))
        price = ex.fetch_ticker(sym)["last"]

        row = {"Activo": sym.replace("/USDT:USDT", "")}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                state, hist, cross, hour, rsi_state, rsi_val = res
                row[f"{label} HA-MACD"] = state
                row[f"{label} HIST"] = hist
                row[f"{label} CRUCE"] = f"{cross} {hour}"
                row[f"{label} RSI"] = f"{rsi_state} ({rsi_val})"
                row[f"{label} MACD REC"] = macd_only_reco(hist, cross)
            else:
                row[f"{label} HA-MACD"] = "-"

        row["RECOMENDACION FINAL"] = full_reco(str(row))
        results.append(row)
        time.sleep(0.1)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V4")

with st.sidebar:
    symbols = get_active_pairs()
    if st.button("🚀 ESCANEAR"):
        st.session_state["sniper_results"] = scan_batch(symbols[:20])

if st.session_state["sniper_results"]:
    st.dataframe(pd.DataFrame(st.session_state["sniper_results"]), use_container_width=True)
