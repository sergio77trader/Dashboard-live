import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide", page_title="KuCoin Scanner por Lotes")

# ==============================
# 1) OBTENER UNIVERSO KUCOIN (BASE)
# ==============================

@st.cache_data(ttl=1800)
def get_kucoin_universe():
    url = "https://api.kucoin.com/api/v1/market/allTickers"
    r = requests.get(url, timeout=10).json()

    if r['code'] != '200000':
        return [], {}

    df = pd.DataFrame(r['data']['ticker'])

    # Solo pares USDT (spot de KuCoin)
    df = df[df['symbol'].str.endswith('-USDT')]
    df['volValue'] = df['volValue'].astype(float)

    # Limpiamos símbolo
    df['coin'] = df['symbol'].str.replace('-USDT', '')

    # Ordenamos por volumen
    df = df.sort_values("volValue", ascending=False)

    coins = df['coin'].tolist()
    vol_map = df.set_index('coin')['volValue'].to_dict()

    return coins, vol_map


ALL_COINS, VOL_MAP = get_kucoin_universe()

# ==============================
# 2) FUNCIÓN DE VELAS (KUCOIN)
# ==============================

def get_kucoin_candles(coin, timeframe, limit=100):
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {
        "symbol": f"{coin}-USDT",
        "type": timeframe,
        "limit": limit
    }

    r = requests.get(url, params=params, timeout=8).json()

    if r.get("code") != "200000":
        return pd.DataFrame()

    df = pd.DataFrame(
        r["data"],
        columns=["Time","Open","Close","High","Low","Vol","Turn"]
    )

    df = df.astype(float)
    df["Time"] = pd.to_datetime(df["Time"], unit="s")
    df = df.sort_values("Time").reset_index(drop=True)
    return df


# ==============================
# 3) AQUÍ VA TU MOTOR (REEMPLAZABLE)
# ==============================

def analyze_asset(coin):
    # EJEMPLO MINIMO (después metés tu HA + MACD + EMA)
    df_5m = get_kucoin_candles(coin, "5min", 100)
    df_1h = get_kucoin_candles(coin, "1hour", 100)
    df_1d = get_kucoin_candles(coin, "1day", 100)

    if df_1d.empty:
        return None

    precio = df_1d["Close"].iloc[-1]
    ultima_hora = df_1h["Time"].iloc[-1]
    ultima_dia = df_1d["Time"].iloc[-1]

    return {
        "Ticker": coin,
        "Precio": precio,
        "Vol_24h": VOL_MAP.get(coin, 0),
        "Ult_1H": ultima_hora,
        "Ult_1D": ultima_dia,
        "Status": "OK"
    }

# ==============================
# 4) SISTEMA POR LOTES DE 50
# ==============================

if "resultados" not in st.session_state:
    st.session_state["resultados"] = []

st.title("KuCoin Scanner por Lotes (Base Correcta)")

batch_size = 50

batches = [
    ALL_COINS[i:i+batch_size]
    for i in range(0, len(ALL_COINS), batch_size)
]

labels = [f"Lote {i+1} ({b[0]} - {b[-1]})" for i,b in enumerate(batches)]

sel = st.selectbox("Elegí Lote:", range(len(batches)),
                   format_func=lambda x: labels[x])

scan = st.button("ESCANEAR LOTE")

if scan:
    targets = batches[sel]

    st.toast(f"Analizando {len(targets)} monedas...", icon="🚀")

    ya_hechos = {r["Ticker"] for r in st.session_state["resultados"]}
    to_run = [c for c in targets if c not in ya_hechos]

    prog = st.progress(0)

    nuevos = []
    for i, coin in enumerate(to_run):
        res = analyze_asset(coin)
        if res:
            nuevos.append(res)

        prog.progress((i+1)/len(to_run))
        time.sleep(0.05)

    st.session_state["resultados"].extend(nuevos)
    st.success(f"Agregadas {len(nuevos)} monedas al tablero")

# ==============================
# 5) TABLA ACUMULATIVA
# ==============================

if st.session_state["resultados"]:
    df = pd.DataFrame(st.session_state["resultados"])

    st.dataframe(
        df.sort_values("Vol_24h", ascending=False),
        use_container_width=True,
        height=700
    )
else:
    st.info("Elegí un lote y apretá ESCANEAR")
