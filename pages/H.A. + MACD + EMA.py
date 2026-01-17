import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

st.set_page_config(page_title="Binance Perpetuos - Señales MTF", layout="wide")
st.title("Binance Perpetuos USDT — Señales MTF (5m,15m,1H,4H,1D)")

# ===================================================
# 1) TRAER PERPETUOS DE BINANCE (FUNCIONA EN STREAMLIT)
# ===================================================

@st.cache_data(ttl=300)
def traer_perpetuos_binance():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"

    try:
        r = requests.get(url, timeout=20)
        data = r.json()["symbols"]
    except Exception as e:
        st.error(f"Error Binance: {e}")
        return pd.DataFrame(columns=["symbol","cripto"])

    filas = []

    for s in data:
        symbol = s["symbol"]
        if symbol.endswith("USDT") and s["contractType"] == "PERPETUAL":
            filas.append({
                "symbol": symbol,
                "cripto": symbol.replace("USDT","")
            })

    df = pd.DataFrame(filas)

    if df.empty:
        return pd.DataFrame(columns=["symbol","cripto"])

    return df.sort_values("cripto").reset_index(drop=True)

# ===================================================
# 2) TRAER VELAS (KLINES)
# ===================================================

def traer_klines(symbol, intervalo):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": intervalo,
        "limit": 150
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
    except:
        return pd.DataFrame(columns=["time","open","close","high","low","volume"])

    if not data:
        return pd.DataFrame(columns=["time","open","close","high","low","volume"])

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","trades","tbbav","tbqav","ignore"
    ])

    df = df[["time","open","high","low","close","volume"]].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df = df.sort_values("time")
    return df.reset_index(drop=True)

# ===================================================
# 3) INDICADORES + SEÑAL (TU LÓGICA ADAPTADA)
# ===================================================

def calcular_heikin_ashi(df):
    if df.empty:
        return df

    ha = pd.DataFrame()
    ha["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

    ha["open"] = 0.0
    ha.loc[0, "open"] = (df.loc[0,"open"] + df.loc[0,"close"]) / 2

    for i in range(1, len(df)):
        ha.loc[i, "open"] = (ha.loc[i-1,"open"] + ha.loc[i-1,"close"]) / 2

    ha["high"] = df[["high","open","close"]].max(axis=1)
    ha["low"]  = df[["low","open","close"]].min(axis=1)
    return ha

def macd_hist(df, fast=12, slow=26, signal=9):
    if df.empty:
        return pd.Series(dtype=float)

    ema_fast = df["close"].ewm(span=fast).mean()
    ema_slow = df["close"].ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal).mean()
    return macd - sig

def calcular_senal(df):
    if df.empty:
        return "SIN DATOS", None

    ha = calcular_heikin_ashi(df)
    hist = macd_hist(df)
    ema200 = df["close"].ewm(span=200).mean()

    ultimo = len(df) - 1
    t = df.loc[ultimo, "time"]

    ha_verde = ha.loc[ultimo, "close"] > ha.loc[ultimo, "open"]
    ha_roja  = ha.loc[ultimo, "close"] < ha.loc[ultimo, "open"]
    hist_pos = hist.iloc[ultimo] > 0
    precio_sobre_ema = df.loc[ultimo, "close"] > ema200.iloc[ultimo]

    if ha_verde and hist_pos and precio_sobre_ema:
        return "COMPRA", t

    if ha_roja and not hist_pos and not precio_sobre_ema:
        return "VENTA", t

    return "NEUTRAL", t

# Temporalidades equivalentes en Binance
TF_MAP = {
    "5m": "5m",
    "15m": "15m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d"
}

# ===================================================
# 4) STREAMLIT UI
# ===================================================

df_all = traer_perpetuos_binance()
total = len(df_all)

st.write(f"Total perpetuos USDT encontrados en Binance: **{total}**")

if total == 0:
    st.error("No se pudieron cargar contratos de Binance.")
    st.stop()

bloque = st.number_input(
    "Bloque (0 = primeros 50)",
    min_value=0,
    max_value=max(0, total//50),
    value=0,
    step=1
)

ejecutar = st.button("🚀 EJECUTAR ANÁLISIS DEL BLOQUE")

inicio = bloque * 50
fin = min(inicio + 50, total)
df_slice = df_all.iloc[inicio:fin].copy()

st.write(f"Analizando filas **{inicio} a {fin}**")

resultados = []

if ejecutar:

    barra = st.progress(0)
    total_filas = len(df_slice)

    for i, (_, row) in enumerate(df_slice.iterrows()):
        sym = row["symbol"]
        cripto = row["cripto"]

        senales = {}
        horas = {}

        for tf, interval in TF_MAP.items():
            df_k = traer_klines(sym, interval)
            s, h = calcular_senal(df_k)

            senales[tf] = s
            horas[tf] = h.strftime("%Y-%m-%d %H:%M") if h is not None else "SIN DATOS"

        resultados.append({
            "Cripto": cripto,
            "5m": senales["5m"],  "Hora 5m": horas["5m"],
            "15m": senales["15m"], "Hora 15m": horas["15m"],
            "1H": senales["1H"],  "Hora 1H": horas["1H"],
            "4H": senales["4H"],  "Hora 4H": horas["4H"],
            "1D": senales["1D"],  "Hora 1D": horas["1D"],
        })

        barra.progress((i+1)/total_filas)

    tabla = pd.DataFrame(resultados)

    st.subheader("📊 Señales Multitemporales")
    st.dataframe(tabla, use_container_width=True)

    csv = tabla.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar CSV",
        csv,
        file_name="binance_senales_mtf.csv",
        mime="text/csv"
    )
