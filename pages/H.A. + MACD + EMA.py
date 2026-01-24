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
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ SNIPER MATRIX V13.5")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 1000000:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
    except: return []

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
# ANÁLISIS TÉCNICO PROFUNDO
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        # Indicadores
        macd = ta.macd(df["close"])
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["Hist"] = macd["MACDh_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # 1. Lógica Sniper (HA + Hist)
        state = "NEUTRO"
        if last["HA_Color"] == 1 and last["Hist"] > prev["Hist"]: state = "LONG"
        elif last["HA_Color"] == -1 and last["Hist"] < prev["Hist"]: state = "SHORT"

        # 2. RSI State
        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        # 3. MACD Meta-Data
        macd_zero = "SOBRE 0" if last["MACD"] > 0 else "BAJO 0"
        hist_dir = "Alcista" if last["Hist"] > prev["Hist"] else "Bajista"
        
        # 4. Cálculo del Cruce (Hora)
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross_time = crosses["dt"].iloc[-1].strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "main_signal": f"{'🟢' if state=='LONG' else '🔴' if state=='SHORT' else '⚪'} {state} | {rsi_state} ({rsi_val})",
            "macd_zero": macd_zero,
            "hist_dir": hist_dir,
            "cross_time": last_cross_time,
            "raw_state": state,
            "raw_macd_zero": macd_zero
        }
    except: return None

# ─────────────────────────────────────────────
# RECOMENDACIONES
# ─────────────────────────────────────────────
def get_recommendation(row):
    longs = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} HA-MACD-RSI", "")))
    shorts = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} HA-MACD-RSI", "")))
    
    # HTF Bias (1D y 4H)
    htf_bull = "SOBRE 0" in str(row.get("1D MACD 0", ""))
    
    if longs >= 5 and htf_bull: return "🔥 COMPRA FUERTE", "BULLISH CONFLUENCE"
    if shorts >= 5 and not htf_bull: return "🩸 VENTA FUERTE", "BEARISH CONFLUENCE"
    if "LONG" in str(row.get("1m HA-MACD-RSI", "")) and not htf_bull: return "⚠️ REBOTE", "SCALP ONLY"
    
    return "⚖️ RANGO", "NO CLEAR TREND"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando mercado...")

    for idx, sym in enumerate(targets):
        clean = sym.replace(":USDT", "").replace("/USDT", "")
        prog.progress((idx + 1) / len(targets), text=f"Procesando {clean}")

        try:
            price = ex.fetch_ticker(sym)["last"]
            row = {"Activo": clean, "Precio": f"{price:,.4f}"}

            for label, tf_code in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf_code, ex, price)
                if res:
                    row[f"{label} HA-MACD-RSI"] = res["main_signal"]
                    row[f"{label} MACD 0"] = res["macd_zero"]
                    row[f"{label} Hist"] = res["hist_dir"]
                    row[f"{label} Cruce"] = res["cross_time"]
                else:
                    for c in ["HA-MACD-RSI", "MACD 0", "Hist", "Cruce"]: row[f"{label} {c}"] = "-"

            rec, strat = get_recommendation(row)
            row["Veredicto"] = rec
            row["Estrategia"] = strat
            results.append(row)
            time.sleep(0.05)
        except: continue
    
    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ Y ESTILOS
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V13.5 (FULL)")

with st.sidebar:
    st.header("Control")
    all_symbols = get_active_pairs()
    if all_symbols:
        batch_size = st.selectbox("Lote", [10, 20, 30, 50], index=1)
        batches = [all_symbols[i:i+batch_size] for i in range(0, len(all_symbols), batch_size)]
        sel = st.selectbox("Seleccionar Lote", range(len(batches)))
        
        if st.button("🚀 EJECUTAR ESCANEO", type="primary"):
            st.session_state["sniper_results"] = scan_batch(batches[sel])

if st.button("Limpiar"):
    st.session_state["sniper_results"] = []
    st.rerun()

def style_matrix(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "ALCISTA", "COMPRA", "RSI↑"]):
            return 'background-color: #d4edda; color: #155724;' # Verde claro
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJISTA", "VENTA", "RSI↓"]):
            return 'background-color: #f8d7da; color: #721c24;' # Rojo claro
        return ''
    return df.style.applymap(apply_color)

if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Reordenar columnas para que Veredicto y Estrategia estén al inicio
    cols_order = ["Activo", "Veredicto", "Estrategia", "Precio"]
    other_cols = [c for c in df_final.columns if c not in cols_order]
    df_final = df_final[cols_order + other_cols]
    
    st.dataframe(style_matrix(df_final), use_container_width=True, height=800)
else:
    st.info("Seleccione un lote y presione Ejecutar Escaneo.")
