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
                valid.append({"symbol": s, "vol": tickers[s]["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
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
# ANÁLISIS POR TEMPORALIDAD
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=150)
        if not ohlcv or len(ohlcv) < 60:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["MACD"] = macd["MACD_12_26_9"]
        df["SIGNAL"] = macd["MACDs_12_26_9"]
        df["HIST"] = macd["MACDh_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)

        df = calculate_heikin_ashi(df)

        # ── MACD HIST DIRECCIÓN
        hist_dir = "Alcista" if df["HIST"].iloc[-1] > df["HIST"].iloc[-2] else "Bajista"

        # ── ÚLTIMO CRUCE MACD
        last_cross_time = "-"
        for i in range(len(df)-1, 1, -1):
            prev = df["MACD"].iloc[i-1] - df["SIGNAL"].iloc[i-1]
            curr = df["MACD"].iloc[i] - df["SIGNAL"].iloc[i]
            if prev <= 0 and curr > 0:
                last_cross_time = (df["dt"].iloc[i] - pd.Timedelta(hours=3)).strftime("%H:%M")
                break
            if prev >= 0 and curr < 0:
                last_cross_time = (df["dt"].iloc[i] - pd.Timedelta(hours=3)).strftime("%H:%M")
                break

        # ── HA + MACD POSICIÓN (LO EXISTENTE)
        position = "NEUTRO"
        last_date = df["dt"].iloc[-1]

        for i in range(1, len(df)):
            if position == "NEUTRO":
                if df["HA_Color"].iloc[i] == 1 and df["HIST"].iloc[i] > df["HIST"].iloc[i-1]:
                    position = "LONG"
                    last_date = df["dt"].iloc[i]
                elif df["HA_Color"].iloc[i] == -1 and df["HIST"].iloc[i] < df["HIST"].iloc[i-1]:
                    position = "SHORT"
                    last_date = df["dt"].iloc[i]

        rsi_val = round(df["RSI"].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        return position, last_date, rsi_state, rsi_val, hist_dir, last_cross_time

    except:
        return None

# ─────────────────────────────────────────────
# RECOMENDACIONES
# ─────────────────────────────────────────────
def macd_recommendation(row):
    bulls = sum("Alcista" in str(row.get(f"MACD HIST {tf}", "")) for tf in TIMEFRAMES)
    bears = sum("Bajista" in str(row.get(f"MACD HIST {tf}", "")) for tf in TIMEFRAMES)

    if bulls >= 5:
        return "📈 MACD ALCISTA"
    if bears >= 5:
        return "📉 MACD BAJISTA"
    return "⚖️ MACD MIXTO"

def final_verdict(row):
    if "COMPRA FUERTE" in row["Estrategia"] and "ALCISTA" in row["Recomendación MACD"]:
        return "🚀 LONG CONFIRMADO"
    if "VENTA FUERTE" in row["Estrategia"] and "BAJISTA" in row["Recomendación MACD"]:
        return "💣 SHORT CONFIRMADO"
    return "⏳ ESPERAR"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0)

    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets))
        price = ex.fetch_ticker(sym)["last"]
        clean = sym.replace(":USDT","").replace("/USDT","")
        row = {"Activo": clean}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                state, date, rsi_state, rsi_val, hist_dir, cross_time = res
                icon = "🟢" if state=="LONG" else "🔴" if state=="SHORT" else "⚪"

                row[f"{label} HA-MACD"] = f"{icon} {state} | {rsi_state} ({rsi_val})"
                row[f"{label} ALERTA"] = (date - pd.Timedelta(hours=3)).strftime("%H:%M")
                row[f"MACD HIST {label}"] = hist_dir
                row[f"CRUCE HORA {label}"] = cross_time
            else:
                row[f"{label} HA-MACD"] = "-"
                row[f"{label} ALERTA"] = "-"
                row[f"MACD HIST {label}"] = "-"
                row[f"CRUCE HORA {label}"] = "-"

        row["Estrategia"] = get_recommendation(row)
        row["Recomendación MACD"] = macd_recommendation(row)
        row["VEREDICTO"] = final_verdict(row)

        results.append(row)
        time.sleep(0.05)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V5")

with st.sidebar:
    with st.spinner("Cargando mercado..."):
        all_symbols = get_active_pairs()

    batch = st.selectbox("Tamaño Lote:", [10,20,30], index=1)
    batches = [all_symbols[i:i+batch] for i in range(0,len(all_symbols),batch)]
    sel = st.selectbox("Seleccionar Lote:", range(len(batches)))

    if st.button("🚀 ESCANEAR"):
        st.session_state["sniper_results"] = scan_batch(batches[sel])

if st.session_state["sniper_results"]:
    st.dataframe(pd.DataFrame(st.session_state["sniper_results"]), use_container_width=True, height=800)
