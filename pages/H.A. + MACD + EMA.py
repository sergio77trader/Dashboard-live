import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

st.set_page_config(page_title="KuCoin Perpetuos - Señales MTF", layout="wide")
st.title("KuCoin Perpetuos USDT.P — Lotes de 50 + Resultados Acumulados")

# ===========================
# SESIÓN PARA ACUMULAR TABLA
# ===========================

if "tabla_acumulada" not in st.session_state:
    st.session_state["tabla_acumulada"] = pd.DataFrame()

# ===================================================
# 1) TRAER LISTADO BASE (SOLO UNA VEZ)
# ===================================================

@st.cache_data(ttl=300)
def traer_perpetuos_kucoin():
    url = "https://api-futures.kucoin.com/api/v1/contracts"

    try:
        r = requests.get(url, timeout=20)
        data = r.json().get("data", [])
    except Exception as e:
        st.error(f"Error consultando KuCoin: {e}")
        return pd.DataFrame(columns=["symbol","cripto"])

    filas = []

    for c in data:
        sym = c.get("symbol", "")
        if sym.endswith("USDT.P"):
            filas.append({
                "symbol": sym,
                "cripto": sym.replace("USDT.P", "")
            })

    df = pd.DataFrame(filas)

    if df.empty:
        return pd.DataFrame(columns=["symbol","cripto"])

    return df.sort_values("cripto").reset_index(drop=True)

# ===================================================
# 2) TRAER VELAS (KLINES)
# ===================================================

def traer_klines(symbol, gran):
    url = "https://api-futures.kucoin.com/api/v1/kline/query"
    params = {
        "symbol": symbol,
        "granularity": gran,
        "limit": 150
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json().get("data", [])
    except:
        return pd.DataFrame(columns=["time","open","high","low","close","volume"])

    if not data:
        return pd.DataFrame(columns=["time","open","high","low","close","volume"])

    df = pd.DataFrame(data, columns=[
        "time","open","close","high","low","volume","turnover"
    ])

    df = df[["time","open","high","low","close","volume"]].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.sort_values("time")
    return df.reset_index(drop=True)

# ===================================================
# 3) INDICADORES (TU LÓGICA)
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

# Temporalidades
TF_MAP = {
    "5m": 5,
    "15m": 15,
    "1H": 60,
    "4H": 240,
    "1D": 1440
}

# ===================================================
# 4) STREAMLIT UI — LOTES DE 50 + ACUMULACIÓN
# ===================================================

df_all = traer_perpetuos_kucoin()
total = len(df_all)

st.write(f"Total perpetuos USDT.P disponibles: **{total}**")

if total == 0:
    st.error("KuCoin no respondió con contratos. Recargá en 30–60 segundos.")
    st.stop()

bloque = st.number_input(
    "Bloque (0 = primeros 50)",
    min_value=0,
    max_value=max(0, total//50),
    value=0,
    step=1
)

ejecutar = st.button("🚀 ANALIZAR ESTE BLOQUE Y ACUMULAR")

inicio = bloque * 50
fin = min(inicio + 50, total)
df_slice = df_all.iloc[inicio:fin].copy()

st.write(f"👉 Analizando filas **{inicio} a {fin}**")

if ejecutar:

    barra = st.progress(0)
    resultados = []
    total_filas = len(df_slice)

    for i, (_, row) in enumerate(df_slice.iterrows()):
        sym = row["symbol"]
        cripto = row["cripto"]

        senales = {}
        horas = {}

        for tf, gran in TF_MAP.items():
            df_k = traer_klines(sym, gran)
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

    nuevo_df = pd.DataFrame(resultados)

    # 👉 ACUMULAMOS RESULTADOS
    st.session_state["tabla_acumulada"] = pd.concat(
        [st.session_state["tabla_acumulada"], nuevo_df],
        ignore_index=True
    )

# ===========================
# MOSTRAR TABLA ACUMULADA
# ===========================

st.subheader("📊 RESULTADOS ACUMULADOS")
st.dataframe(st.session_state["tabla_acumulada"], use_container_width=True)

csv = st.session_state["tabla_acumulada"].to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar CSV acumulado",
    csv,
    file_name="kucoin_senales_acumuladas.csv",
    mime="text/csv"
)
