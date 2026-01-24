import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="HA + MACD + RSI Dashboard")

exchange = ccxt.binance({
    "enableRateLimit": True
})

symbol = "BTC/USDT"
timeframes = ["1m", "5m", "15m"]

limit = 200

# ---------------- FUNCTIONS ----------------
def get_data(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
    df = pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"]
    )
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df


def analyze_tf(tf):
    df = get_data(symbol, tf)

    # --- Heikin Ashi ---
    ha = ta.ha(df["open"], df["high"], df["low"], df["close"])
    df["ha_close"] = ha["HA_close"]
    df["ha_open"] = ha["HA_open"]

    ha_trend = "🟢 LONG" if df["ha_close"].iloc[-2] > df["ha_open"].iloc[-2] else "🔴 SHORT"

    # --- MACD ---
    macd = ta.macd(df["close"])
    df["macd"] = macd["MACD_12_26_9"]
    df["signal"] = macd["MACDs_12_26_9"]
    df["hist"] = macd["MACDh_12_26_9"]

    hist_state = (
        "Alcista"
        if df["hist"].iloc[-2] > df["hist"].iloc[-3]
        else "Bajista"
    )

    # Cruce MACD última vela cerrada
    cruce = "—"
    hora_cruce = "—"

    if (
        df["macd"].iloc[-3] < df["signal"].iloc[-3]
        and df["macd"].iloc[-2] > df["signal"].iloc[-2]
    ):
        cruce = "Alcista"
        hora_cruce = df["time"].iloc[-2].strftime("%H:%M")

    elif (
        df["macd"].iloc[-3] > df["signal"].iloc[-3]
        and df["macd"].iloc[-2] < df["signal"].iloc[-2]
    ):
        cruce = "Bajista"
        hora_cruce = df["time"].iloc[-2].strftime("%H:%M")

    # --- RSI ---
    rsi = ta.rsi(df["close"], length=14)
    rsi_val = round(rsi.iloc[-2], 1)

    rsi_state = "RSI↑" if rsi_val > 50 else "RSI↓"

    alerta = f"{ha_trend} | {rsi_state} ({rsi_val})"

    # --- Estrategia ---
    if ha_trend.startswith("🟢") and hist_state == "Alcista":
        estrategia = "COMPRA FUERTE"
    elif ha_trend.startswith("🔴") and hist_state == "Bajista":
        estrategia = "VENTA FUERTE"
    else:
        estrategia = "ESPERAR"

    return {
        "TEMPORALIDAD HA-MACD": f"{tf} HA-MACD",
        "ALERTA": alerta,
        "MACD HIST": hist_state,
        "CRUCE MACD": cruce,
        "HORA CRUCE": hora_cruce,
        "ESTRATEGIA": estrategia
    }

# ---------------- UI ----------------
st.title("📊 H.A. + MACD + RSI (Última vela cerrada)")

rows = []
for tf in timeframes:
    rows.append(analyze_tf(tf))

df_final = pd.DataFrame(rows)

st.dataframe(
    df_final,
    use_container_width=True,
    hide_index=True
)
