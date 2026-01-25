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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V24.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m":"1m", "5m":"5m", "15m":"15m",
    "30m":"30m", "1H":"1h", "4H":"4h", "1D":"1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})
    ex.load_markets()
    return ex

@st.cache_data(ttl=300)
def get_active_pairs(min_volume=100000):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
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
# ANALISIS TÉCNICO (H.A./MACD Y HORA = SCRIPT 1)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(
            ohlcv, columns=["time", "open", "high", "low", "close", "vol"]
        )
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["Hist"]   = macd["MACDh_12_26_9"]
        df["MACD"]   = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["RSI"]    = ta.rsi(df["close"], length=14)

        df = calculate_heikin_ashi(df)

        # ── LOGICA SECUENCIAL (SCRIPT 1)
        position = "NEUTRO"
        last_date = df["dt"].iloc[-1]

        for i in range(1, len(df)):
            hist = df["Hist"].iloc[i]
            prev_hist = df["Hist"].iloc[i - 1]
            ha_color = df["HA_Color"].iloc[i]
            date = df["dt"].iloc[i]

            if position == "LONG" and hist < prev_hist:
                position = "NEUTRO"
            elif position == "SHORT" and hist > prev_hist:
                position = "NEUTRO"

            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist:
                    position = "LONG"
                    last_date = date
                elif ha_color == -1 and hist < prev_hist:
                    position = "SHORT"
                    last_date = date

        icon = "🟢" if position == "LONG" else "🔴" if position == "SHORT" else "⚪"

        rsi_val = round(df["RSI"].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        signal = f"{icon} {position} | {rsi_state} ({rsi_val})"
        signal_time = (last_date - pd.Timedelta(hours=3)).strftime("%H:%M")

        # ── RESTO ORIGINAL SCRIPT 2
        h_dir = "ALCISTA" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJISTA"
        m0 = "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0"

        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"]]
        cross_time = (
            (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M")
            if not crosses.empty else "--:--"
        )

        return {
            "signal": signal,
            "signal_time": signal_time,
            "m0": m0,
            "h_dir": h_dir,
            "cross_time": cross_time
        }

    except:
        return None

# ─────────────────────────────────────────────
# VEREDICTO (ORIGINAL)
# ─────────────────────────────────────────────
def get_verdict(row):
    bulls = sum(1 for tf in TIMEFRAMES if any(x in str(row.get(f"{tf} H.A./MACD","")) for x in ["LONG","ALCISTA"]))
    bears = sum(1 for tf in TIMEFRAMES if any(x in str(row.get(f"{tf} H.A./MACD","")) for x in ["SHORT","BAJISTA"]))
    bias_1d = str(row.get("1D MACD 0", ""))

    if bulls >= 5 and "SOBRE 0" in bias_1d:
        return "🔥 COMPRA FUERTE", "MTF CONFLUENCE BULL"
    if bears >= 5 and "BAJO 0" in bias_1d:
        return "🩸 VENTA FUERTE", "MTF CONFLUENCE BEAR"
    if "LONG" in str(row.get("1m H.A./MACD", "")):
        return "💎 GIRO PROBABLE", "PULLBACK DETECTED"

    return "⚖️ RANGO", "NO TREND"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets, accumulate=True):
    ex = get_exchange()
    new_results = []
    prog = st.progress(0)

    for idx, sym in enumerate(targets):
        clean = sym.split(":")[0].replace("/USDT", "")
        prog.progress((idx+1)/len(targets), text=f"Analizando {clean}...")

        try:
            p = ex.fetch_ticker(sym)["last"]
            row = {"Activo": clean, "Precio": f"{p:,.4f}"}

            for label, tf in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf, ex, p)
                if res:
                    row[f"{label} H.A./MACD"] = res["signal"]
                    row[f"{label} Hora Señal"] = res["signal_time"]
                    row[f"{label} MACD 0"] = res["m0"]
                    row[f"{label} Hist."] = res["h_dir"]
                    row[f"{label} Cruce MACD"] = res["cross_time"]
                else:
                    for c in ["H.A./MACD","Hora Señal","MACD 0","Hist.","Cruce MACD"]:
                        row[f"{label} {c}"] = "-"

            v, e = get_verdict(row)
            row["VEREDICTO"] = v
            row["ESTRATEGIA"] = e

            new_results.append(row)
            time.sleep(0.05)

        except:
            continue

    prog.empty()

    if accumulate:
        current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in new_results:
            current[r["Activo"]] = r
        return list(current.values())

    return new_results

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("Radar Control")

    all_sym = get_active_pairs(min_volume=0)
    b_size = st.selectbox("Batch", [20, 50, 100], index=1)
    batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
    sel = st.selectbox("Lote", range(len(batches)))
    accumulate = st.checkbox("Acumular", value=True)

    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        if batches:
            st.session_state["sniper_results"] = scan_batch(batches[sel], accumulate)

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    st.dataframe(df, use_container_width=True, height=800)
else:
    st.info("👈 Presione INICIAR ESCANEO.")
