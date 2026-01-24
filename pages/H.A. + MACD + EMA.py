import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# ===============================
# CONFIG
# ===============================
st.set_page_config(layout="wide", page_title="SystemaTrader – MACD / RSI Matrix")

SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
TIMEFRAMES = {
    "1m": "1m",
    "5m": "5m"
}

RSI_LEN = 14

exchange = ccxt.binance()

# ===============================
# UTILS
# ===============================
def heikin_ashi(df):
    ha = df.copy()
    ha["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha["HA_Open"] = 0.0
    ha.iloc[0, ha.columns.get_loc("HA_Open")] = (df.iloc[0]["open"] + df.iloc[0]["close"]) / 2

    for i in range(1, len(df)):
        ha.iloc[i, ha.columns.get_loc("HA_Open")] = (
            ha.iloc[i - 1]["HA_Open"] + ha.iloc[i - 1]["HA_Close"]
        ) / 2

    ha["HA_High"] = ha[["HA_Open", "HA_Close", "high"]].max(axis=1)
    ha["HA_Low"] = ha[["HA_Open", "HA_Close", "low"]].min(axis=1)
    return ha


def analyze_ticker_tf(symbol, tf, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=120)
        df = pd.DataFrame(
            ohlcv, columns=["time", "open", "high", "low", "close", "volume"]
        )
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df.set_index("time", inplace=True)

        # Heikin Ashi
        ha = heikin_ashi(df)

        # MACD
        macd = ta.macd(ha["HA_Close"])
        ha = pd.concat([ha, macd], axis=1)

        # RSI
        ha["RSI"] = ta.rsi(ha["HA_Close"], length=RSI_LEN)

        last = ha.iloc[-1]
        prev = ha.iloc[-2]

        # Estado HA + MACD
        if last["HA_Close"] > last["HA_Open"] and last["MACDh_12_26_9"] > 0:
            state = "LONG"
        elif last["HA_Close"] < last["HA_Open"] and last["MACDh_12_26_9"] < 0:
            state = "SHORT"
        else:
            state = "NEUTRO"

        # RSI
        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if last["RSI"] > prev["RSI"] else "RSI↓"

        # Histograma
        hist_state = (
            "ALCISTA"
            if last["MACDh_12_26_9"] > prev["MACDh_12_26_9"]
            else "BAJISTA"
        )

        # Cruce MACD
        cross_type = "-"
        cross_time = "-"

        if (
            prev["MACD_12_26_9"] < prev["MACDs_12_26_9"]
            and last["MACD_12_26_9"] > last["MACDs_12_26_9"]
        ):
            cross_type = "CRUCE ALCISTA"
            cross_time = last.name.strftime("%H:%M")

        if (
            prev["MACD_12_26_9"] > prev["MACDs_12_26_9"]
            and last["MACD_12_26_9"] < last["MACDs_12_26_9"]
        ):
            cross_type = "CRUCE BAJISTA"
            cross_time = last.name.strftime("%H:%M")

        return {
            "state": state,
            "rsi_state": rsi_state,
            "rsi_val": rsi_val,
            "hist_state": hist_state,
            "cross_type": cross_type,
            "cross_time": cross_time,
            "time": last.name.strftime("%H:%M"),
        }

    except Exception as e:
        return None


# ===============================
# UI
# ===============================
st.title("📊 SystemaTrader – MACD / RSI Multi-TF")

rows = []

for sym in SYMBOLS:
    ticker = exchange.fetch_ticker(sym)
    px = ticker["last"]

    row = {
        "SYMBOL": sym,
        "PRECIO": round(px, 2),
    }

    for label, tf in TIMEFRAMES.items():
        res = analyze_ticker_tf(sym, tf, exchange, px)

        if res:
            icon = "🟢" if res["state"] == "LONG" else "🔴" if res["state"] == "SHORT" else "⚪"
            row[f"{label} HA-MACD"] = f"{icon} {res['state']} | {res['rsi_state']} ({res['rsi_val']})"
            row[f"{label} ALERTA"] = res["time"]
            row[f"{label} MACD HIST"] = res["hist_state"]
            row[f"{label} CRUCE MACD"] = res["cross_type"]
            row[f"{label} HORA CRUCE"] = res["cross_time"]
        else:
            row[f"{label} HA-MACD"] = "-"
            row[f"{label} ALERTA"] = "-"
            row[f"{label} MACD HIST"] = "-"
            row[f"{label} CRUCE MACD"] = "-"
            row[f"{label} HORA CRUCE"] = "-"

    rows.append(row)

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True)
