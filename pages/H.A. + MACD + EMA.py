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
                valid.append({
                    "symbol": s,
                    "vol": tickers[s]["quoteVolume"]
                })

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
# MACD ANALYSIS
# ─────────────────────────────────────────────
def analyze_macd(df):
    hist = df["Hist"]

    last_cross_dir = "Sin cruce"
    last_cross_time = df["dt"].iloc[-1]

    for i in range(1, len(hist)):
        if hist.iloc[i-1] < 0 and hist.iloc[i] > 0:
            last_cross_dir = "Alcista"
            last_cross_time = df["dt"].iloc[i]
        elif hist.iloc[i-1] > 0 and hist.iloc[i] < 0:
            last_cross_dir = "Bajista"
            last_cross_time = df["dt"].iloc[i]

    momentum = "Acelerando ↑" if hist.iloc[-1] > hist.iloc[-2] else "Perdiendo ↓"

    return last_cross_dir, momentum, last_cross_time

# ─────────────────────────────────────────────
# ANÁLISIS POR TEMPORALIDAD
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=120)
        if not ohlcv or len(ohlcv) < 60:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(
            ohlcv,
            columns=["time", "open", "high", "low", "close", "vol"]
        )
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["Hist"] = macd["MACDh_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)

        df = calculate_heikin_ashi(df)

        macd_dir, momentum, cross_time = analyze_macd(df)

        rsi_val = round(df["RSI"].iloc[-1], 1)
        if rsi_val > 55:
            rsi_state = "RSI↑"
        elif rsi_val < 45:
            rsi_state = "RSI↓"
        else:
            rsi_state = "RSI="

        return macd_dir, momentum, cross_time, rsi_state, rsi_val

    except:
        return None

# ─────────────────────────────────────────────
# ESTRATEGIA
# ─────────────────────────────────────────────
def get_strategy(row):
    bull = sum("Alcista" in str(row.get(f"{tf} MACD", "")) for tf in TIMEFRAMES)
    bear = sum("Bajista" in str(row.get(f"{tf} MACD", "")) for tf in TIMEFRAMES)

    if bull >= 5:
        return "📈 BIAS ALCISTA"
    if bear >= 5:
        return "📉 BIAS BAJISTA"

    return "⚖️ NEUTRO"

def get_veredicto(row):
    if "BIAS ALCISTA" in row["Estrategia"] and "Acelerando" in str(row.get("1m MOMENTUM", "")):
        return "🚀 LONG CONFIRMADO"
    if "BIAS BAJISTA" in row["Estrategia"] and "Acelerando" in str(row.get("1m MOMENTUM", "")):
        return "🩸 SHORT CONFIRMADO"
    return "🟡 ESPERAR"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Iniciando radar...")

    for idx, sym in enumerate(targets):
        clean = sym.replace(":USDT", "").replace("/USDT", "")
        prog.progress((idx + 1) / len(targets), text=f"Analizando {clean}")

        try:
            price = ex.fetch_ticker(sym)["last"]
        except:
            continue

        row = {"Activo": clean}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                macd_dir, momentum, cross_time, rsi_state, rsi_val = res
                hora = (cross_time - pd.Timedelta(hours=3)).strftime("%H:%M")

                row[f"{label} MACD"] = macd_dir
                row[f"{label} MOMENTUM"] = momentum
                row[f"{label} CRUCE"] = hora
                row[f"{label} RSI"] = f"{rsi_state} ({rsi_val})"
            else:
                row[f"{label} MACD"] = "-"
                row[f"{label} MOMENTUM"] = "-"
                row[f"{label} CRUCE"] = "-"
                row[f"{label} RSI"] = "-"

        row["Estrategia"] = get_strategy(row)
        row["VEREDICTO"] = get_veredicto(row)

        results.append(row)
        time.sleep(0.1)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V5")
st.caption("MACD 0 + Momentum + RSI | KuCoin Futures")

with st.sidebar:
    st.header("Configuración")

    with st.spinner("Cargando mercado..."):
        all_symbols = get_active_pairs()

    if all_symbols:
        batch_size = st.selectbox("Tamaño Lote:", [10, 20, 30, 50], index=1)
        batches = [
            all_symbols[i:i + batch_size]
            for i in range(0, len(all_symbols), batch_size)
        ]

        sel = st.selectbox("Seleccionar Lote:", range(len(batches)))

        if st.button("🚀 ESCANEAR"):
            st.session_state["sniper_results"] = scan_batch(batches[sel])
    else:
        st.error("Error de conexión.")

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    st.dataframe(df, use_container_width=True, height=800)
else:
    st.info("👈 Seleccioná un lote para comenzar.")
