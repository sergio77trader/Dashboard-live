import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime, timezone, timedelta
import numpy as np

st.set_page_config(page_title="KuCoin Scanner", layout="wide")

BASE_URL = "https://api-futures.kucoin.com"

# ===============================
# UTILIDADES
# ===============================

def hora_argentina():
    return datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=-3))
    )

def fetch_klines(symbol, tf, limit=50):
    """
    Trae velas de KuCoin Futures (USDT-M)
    """
    url = f"{BASE_URL}/api/v1/kline/query"
    params = {
        "symbol": symbol,
        "granularity": tf,
        "limit": limit
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if data.get("code") != "200000":
        return None

    cols = ["ts","open","close","high","low","volume","turnover"]
    df = pd.DataFrame(data["data"], columns=cols)
    df = df.astype(float)
    df["ts"] = pd.to_datetime(df["ts"], unit="s")
    df = df.sort_values("ts")
    return df

def macd_signal(df, fast=12, slow=26, signal=9):
    df["ema_fast"] = df["close"].ewm(span=fast).mean()
    df["ema_slow"] = df["close"].ewm(span=slow).mean()
    df["macd"] = df["ema_fast"] - df["ema_slow"]
    df["signal"] = df["macd"].ewm(span=signal).mean()

    if df.iloc[-1]["macd"] > df.iloc[-1]["signal"]:
        return "COMPRA"
    elif df.iloc[-1]["macd"] < df.iloc[-1]["signal"]:
        return "VENTA"
    else:
        return "ESPERA"

# ===============================
# TRAER CONTRATOS POR LOTES
# ===============================

@st.cache_data(ttl=60)
def traer_perpetuos_usdtp_por_lotes(lote_size=50):

    url = f"{BASE_URL}/api/v1/contracts/active"
    r = requests.get(url, timeout=15)
    data = r.json()

    if data.get("code") != "200000":
        st.error("KuCoin no respondió. Probá en 30–60 segundos.")
        return pd.DataFrame()

    symbols = [
        c["symbol"] 
        for c in data["data"] 
        if c["symbol"].endswith("USDTM")
    ]

    st.write(f"Total contratos USDT-M encontrados: {len(symbols)}")

    resultados = []

    timeframes = {
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1D": 86400
    }

    now_ar = hora_argentina()
    fecha = now_ar.strftime("%Y-%m-%d")
    hora = now_ar.strftime("%H:%M:%S")

    for i in range(0, len(symbols), lote_size):
        lote = symbols[i:i+lote_size]
        st.write(f"Procesando lote {i} → {i+lote_size}")

        for s in lote:
            fila = {
                "cripto": s.replace("USDTM", "USDT.P"),
                "fecha": fecha,
                "hora": hora
            }

            for nombre_tf, segundos in timeframes.items():
                df_kl = fetch_klines(s, segundos, limit=60)

                if df_kl is None or len(df_kl) < 30:
                    fila[f"{nombre_tf}_señal"] = "SIN DATOS"
                else:
                    fila[f"{nombre_tf}_señal"] = macd_signal(df_kl)

            resultados.append(fila)
            time.sleep(0.8)

        time.sleep(2)

    return pd.DataFrame(resultados)

# ===============================
# STREAMLIT UI
# ===============================

st.title("Scanner KuCoin Perpetuos (Base Operativa)")

df = traer_perpetuos_usdtp_por_lotes(lote_size=50)

if df.empty:
    st.stop()

orden = [
    "cripto",
    "fecha",
    "hora",
    "5m_señal",
    "15m_señal",
    "1h_señal",
    "4h_señal",
    "1D_señal"
]

df = df[orden]

st.dataframe(df, use_container_width=True)

st.success("Base funcional lista. Ahora podemos meter TU lógica exacta de H.A + EMA + MACD.")
