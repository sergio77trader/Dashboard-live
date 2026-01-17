import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timezone, timedelta

# ===========================
# CONFIGURACIÓN
# ===========================
TF_MAP = {
    "5m":  "5min",
    "15m": "15min",
    "1H":  "1hour",
    "4H":  "4hour",
    "1D":  "1day",
}

ARG_TZ = timezone(timedelta(hours=-3))

# ===========================
# FUNCIONES AUXILIARES
# ===========================

@st.cache_data(ttl=60)
def cargar_perpetuos_kucoin():
    url = "https://api-futures.kucoin.com/api/v1/contracts/active"
    r = requests.get(url, timeout=20).json()

    filas = []
    for it in r.get("data", []):
        if it.get("expireDate") is None and it.get("symbol","").endswith("USDTM"):
            filas.append({
                "cripto": it["baseCurrency"],
                "symbol": it["symbol"]
            })

    df = pd.DataFrame(filas).drop_duplicates("symbol").reset_index(drop=True)
    return df

def traer_klines(symbol, interval):
    url = "https://api-futures.kucoin.com/api/v1/kline/query"
    params = {
        "symbol": symbol,
        "granularity": interval,
        "limit": 120
    }
    r = requests.get(url, params=params, timeout=20).json()
    data = r.get("data", [])

    if not data:
        return None

    cols = ["ts","open","high","low","close","vol"]
    df = pd.DataFrame(data, columns=cols)
    df = df.astype(float)
    df["ts"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(ARG_TZ)
    return df.sort_values("ts")

def calcular_senal(df):
    if df is None or len(df) < 30:
        return "SS", None

    o,h,l,c = df["open"], df["high"], df["low"], df["close"]

    # --- Heikin Ashi ---
    ha_close = (o+h+l+c)/4
    ha_open = (o+c)/2
    ha_open = ha_open.rolling(2).mean().fillna(ha_open)

    ha_verde = ha_close.iloc[-1] > ha_open.iloc[-1]

    # --- MACD ---
    fast = c.ewm(12).mean()
    slow = c.ewm(26).mean()
    macd = fast - slow
    signal = macd.ewm(9).mean()
    hist = macd - signal

    hist_sube = hist.iloc[-1] > hist.iloc[-2]
    hist_baja = hist.iloc[-1] < hist.iloc[-2]

    # --- EMA 200 ---
    ema200 = c.ewm(200).mean()
    precio_arriba = c.iloc[-1] > ema200.iloc[-1]
    precio_abajo = c.iloc[-1] < ema200.iloc[-1]

    hora = df["ts"].iloc[-1].strftime("%H:%M")

    if ha_verde and hist_sube and precio_arriba:
        return "COMPRA", hora
    if (not ha_verde) and hist_baja and precio_abajo:
        return "VENTA", hora

    return "SS", hora

def sesgo_general(filas):
    conteo = filas.value_counts()
    if conteo.get("COMPRA",0) >= 3:
        return "ALCISTA"
    if conteo.get("VENTA",0) >= 3:
        return "BAJISTA"
    return "NEUTRAL"

# ===========================
# APP STREAMLIT
# ===========================

st.title("KuCoin — Perpetuos Multitemporales (bloques de 50)")

df_all = cargar_perpetuos_kucoin()
total = len(df_all)

st.write(f"Total perpetuos USDTM encontrados hoy: **{total}**")

bloque = st.number_input(
    "Bloque (0 = primeros 50)",
    min_value=0,
    max_value=max(0, total//50),
    value=0,
    step=1
)

inicio = bloque*50
fin = inicio+50
df_slice = df_all.iloc[inicio:fin].reset_index(drop=True)

# Contenedor para resultados
resultados = []

for _, row in df_slice.iterrows():
    sym = row["symbol"]
    cripto = row["cripto"]

    senales = {}
    horas = {}

    for tf, gran in TF_MAP.items():
        df_k = traer_klines(sym, gran)
        s, h = calcular_senal(df_k)
        senales[tf] = s
        horas[tf] = h

    sesgo = sesgo_general(pd.Series(senales.values()))

    resultados.append({
        "Cripto": cripto,
        "5m": senales["5m"], "Hora 5m": horas["5m"],
        "15m": senales["15m"], "Hora 15m": horas["15m"],
        "1H": senales["1H"], "Hora 1H": horas["1H"],
        "4H": senales["4H"], "Hora 4H": horas["4H"],
        "1D": senales["1D"], "Hora 1D": horas["1D"],
        "Sesgo": sesgo
    })

tabla = pd.DataFrame(resultados)
st.subheader(f"Mostrando filas {inicio} a {min(fin,total)}")
st.dataframe(tabla)

# -------- ACUMULADO ----------
if "acumulado" not in st.session_state:
    st.session_state["acumulado"] = pd.DataFrame()

if st.button("Agregar estas 50 con señales"):
    st.session_state["acumulado"] = (
        pd.concat([st.session_state["acumulado"], tabla])
        .drop_duplicates()
        .reset_index(drop=True)
    )

st.subheader("Mi lista acumulada")
st.dataframe(st.session_state["acumulado"])

csv = st.session_state["acumulado"].to_csv(index=False).encode("utf-8")

st.download_button(
    "Descargar CSV",
    data=csv,
    file_name="kucoin_perpetuos_senales.csv",
    mime="text/csv"
)
