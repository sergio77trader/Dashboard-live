import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="SystemaTrader – HA MACD RSI Matrix")

exchange = ccxt.binance()

symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
timeframes = ["1m", "5m", "15m"]

# ---------------- SESSION STATE (ACUMULACIÓN) ----------------
if "results" not in st.session_state:
    st.session_state.results = []

# ---------------- FUNCIONES ----------------
def get_data(symbol, tf, limit=150):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df

def heikin_ashi(df):
    ha = df.copy()
    ha["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha["ha_open"] = ha["ha_close"].shift(1)
    ha["ha_open"].iloc[0] = df["open"].iloc[0]
    ha["ha_high"] = ha[["ha_open","ha_close","high"]].max(axis=1)
    ha["ha_low"]  = ha[["ha_open","ha_close","low"]].min(axis=1)
    return ha

# ---------------- SCAN ----------------
def scan():
    rows = []

    for symbol in symbols:
        row = {"Symbol": symbol}

        estrategia_score = 0

        for tf in timeframes:
            df = get_data(symbol, tf)
            ha = heikin_ashi(df)

            macd = ta.macd(df["close"])
            rsi = ta.rsi(df["close"], length=14)

            ha_green = ha["ha_close"].iloc[-1] > ha["ha_open"].iloc[-1]
            macd_up = macd["MACD_12_26_9"].iloc[-1] > macd["MACDs_12_26_9"].iloc[-1]
            rsi_val = round(rsi.iloc[-1], 1)
            rsi_up = rsi_val > 50

            # --------- ESTADO ---------
            if ha_green and macd_up:
                state = "LONG"
                icon = "🟢"
                estrategia_score += 1
            elif not ha_green and not macd_up:
                state = "SHORT"
                icon = "🔴"
                estrategia_score -= 1
            else:
                state = "NEUTRO"
                icon = "🟡"

            rsi_state = "RSI↑" if rsi_up else "RSI↓"
            alert_time = df["time"].iloc[-1].strftime("%H:%M")

            # --------- COLUMNAS ---------
            # ORIGINAL (ACUMULADA)
            row[tf] = f"{icon} {state}"

            # NUEVA – TODO JUNTO (SIN HORA)
            row[f"{tf} HA-MACD"] = f"{icon} {state} | {rsi_state} ({rsi_val})"

            # NUEVA – SOLO HORA
            row[f"{tf} ALERTA"] = alert_time

        # --------- ESTRATEGIA GLOBAL ---------
        if estrategia_score >= 2:
            row["Estrategia"] = "COMPRA FUERTE"
        elif estrategia_score == 1:
            row["Estrategia"] = "COMPRA"
        elif estrategia_score <= -2:
            row["Estrategia"] = "VENTA FUERTE"
        elif estrategia_score == -1:
            row["Estrategia"] = "VENTA"
        else:
            row["Estrategia"] = "ESPERAR"

        rows.append(row)

    return pd.DataFrame(rows)

# ---------------- EJECUCIÓN ----------------
df_scan = scan()

# ACUMULACIÓN (NO SE BORRA)
st.session_state.results.append(df_scan)

df_final = pd.concat(st.session_state.results).drop_duplicates(
    subset=["Symbol"], keep="last"
)

# ---------------- UI ----------------
st.title("📊 SystemaTrader – HA + MACD + RSI")
st.dataframe(df_final, use_container_width=True)
