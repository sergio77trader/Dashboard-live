import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide", page_title="HA + MACD + EMA KuCoin Scanner")

# =====================================================
# 1) OBTENER UNIVERSO KUCOIN (BASE CONFIABLE)
# =====================================================

@st.cache_data(ttl=1800)
def get_kucoin_universe():
    url = "https://api.kucoin.com/api/v1/market/allTickers"
    r = requests.get(url, timeout=10).json()

    if r.get("code") != "200000":
        return [], {}

    df = pd.DataFrame(r["data"]["ticker"])
    df = df[df["symbol"].str.endswith("-USDT")]
    df["volValue"] = df["volValue"].astype(float)
    df["coin"] = df["symbol"].str.replace("-USDT", "")

    df = df.sort_values("volValue", ascending=False)

    coins = df["coin"].tolist()
    vol_map = df.set_index("coin")["volValue"].to_dict()

    return coins, vol_map


ALL_COINS, VOL_MAP = get_kucoin_universe()

# =====================================================
# 2) DESCARGA DE VELAS KUCOIN
# =====================================================

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

# =====================================================
# 3) INDICADORES (TU LÓGICA)
# =====================================================

def calc_heikin_ashi(df):
    if df.empty:
        return 0

    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [(df["Open"].iloc[0] + df["Close"].iloc[0]) / 2]

    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha_close.iloc[i-1]) / 2)

    last_open = ha_open[-1]
    last_close = ha_close.iloc[-1]

    return 1 if last_close > last_open else -1


def calc_macd_hist(df):
    if df.empty:
        return 0

    fast = df["Close"].ewm(span=12).mean()
    slow = df["Close"].ewm(span=26).mean()
    macd = fast - slow
    signal = macd.ewm(span=9).mean()
    hist = macd - signal

    return hist.iloc[-1] - hist.iloc[-2]


def calc_ema200(df):
    if df.empty:
        return None
    return df["Close"].ewm(span=200).mean().iloc[-1]


def get_signal(df):
    ha = calc_heikin_ashi(df)
    macd_move = calc_macd_hist(df)
    ema200 = calc_ema200(df)

    if df.empty or ema200 is None:
        return "⚠️ SIN DATOS"

    price = df["Close"].iloc[-1]

    long_ok = (ha == 1) and (macd_move > 0) and (price > ema200)
    short_ok = (ha == -1) and (macd_move < 0) and (price < ema200)

    if long_ok:
        return "🟢 LONG"
    if short_ok:
        return "🔴 SHORT"
    return "⚠️ ESPERAR"

# =====================================================
# 4) MOTOR DE ANÁLISIS POR ACTIVO
# =====================================================

def analyze_asset(coin):

    tf_map = {
        "5m": "5min",
        "15m": "15min",
        "1H": "1hour",
        "4H": "4hour",
        "1D": "1day"
    }

    results = {"Ticker": coin}

    ema_bias = []
    macd_bias = []

    for label, tf in tf_map.items():
        df = get_kucoin_candles(coin, tf, 100)

        if df.empty:
            results[f"Señal_{label}"] = "⚠️ SIN DATOS"
            results[f"Hora_{label}"] = None
            continue

        signal = get_signal(df)
        results[f"Señal_{label}"] = signal
        results[f"Hora_{label}"] = df["Time"].iloc[-1]

        ema200 = calc_ema200(df)
        price = df["Close"].iloc[-1]
        macd_move = calc_macd_hist(df)

        ema_bias.append(1 if price > ema200 else -1)
        macd_bias.append(1 if macd_move > 0 else -1)

    results["EMA200_bias"] = (
        "BULLISH" if sum(ema_bias) > 0 else "BEARISH" if sum(ema_bias) < 0 else "MIXTO"
    )

    results["MACD_bias"] = (
        "BULLISH" if sum(macd_bias) > 0 else "BEARISH" if sum(macd_bias) < 0 else "MIXTO"
    )

    df_d = get_kucoin_candles(coin, "1day", 1)
    results["Precio"] = df_d["Close"].iloc[-1] if not df_d.empty else np.nan
    results["Vol_24h"] = VOL_MAP.get(coin, 0)

    return results

# =====================================================
# 5) STREAMLIT UI + LOTES DE 50
# =====================================================

if "resultados" not in st.session_state:
    st.session_state["resultados"] = []

st.title("🎯 HA + MACD + EMA — KuCoin Scanner")

batch_size = 50
batches = [ALL_COINS[i:i+batch_size] for i in range(0, len(ALL_COINS), batch_size)]
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
        try:
            res = analyze_asset(coin)
            nuevos.append(res)
        except:
            pass

        prog.progress((i+1)/len(to_run))
        time.sleep(0.05)

    st.session_state["resultados"].extend(nuevos)
    st.success(f"Agregadas {len(nuevos)} monedas al tablero")

# =====================================================
# 6) TABLA FINAL (FORMATO QUE APROBASTE)
# =====================================================

if st.session_state["resultados"]:
    df = pd.DataFrame(st.session_state["resultados"])

    cols_order = [
        "Ticker","Precio","Vol_24h",
        "Señal_5m","Hora_5m",
        "Señal_15m","Hora_15m",
        "Señal_1H","Hora_1H",
        "Señal_4H","Hora_4H",
        "Señal_1D","Hora_1D",
        "EMA200_bias","MACD_bias"
    ]

    df = df[cols_order]

    st.dataframe(
        df.sort_values("Vol_24h", ascending=False),
        use_container_width=True,
        height=700
    )

else:
    st.info("👈 Elegí un lote y apretá ESCANEAR")
