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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V18.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {"1m":"1m", "5m":"5m", "15m":"15m", "30m":"30m", "1H":"1h", "4H":"4h", "1D":"1d"}

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
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 1000000]
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
# ANÁLISIS TÉCNICO
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        macd = ta.macd(df["close"])
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        hist_val, hist_prev = last["Hist"], prev["Hist"]
        ha_color = last["HA_Color"]
        phase, icon = "NEUTRO", "⚪"
        
        if ha_color == 1 and hist_val > hist_prev:
            if hist_val < 0: phase, icon = "PULLBACK ALCISTA", "🔵"
            else: phase, icon = "CONFIRMACION BULL", "🟢"
        elif ha_color == -1 and hist_val < hist_prev:
            if hist_val > 0: phase, icon = "PULLBACK BAJISTA", "🟠"
            else: phase, icon = "CONFIRMACION BEAR", "🔴"

        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "signal": f"{icon} {phase} | {rsi_state} ({rsi_val})",
            "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if hist_val > hist_prev else "BAJISTA",
            "cross_time": last_cross,
            "signal_time": (last["dt"] - pd.Timedelta(hours=3)).strftime("%H:%M")
        }
    except: return None

def get_verdict(row):
    bulls = sum(1 for tf in TIMEFRAMES if any(x in str(row.get(f"{tf} H.A./MACD","")) for x in ["BULL", "ALCISTA"]))
    bears = sum(1 for tf in TIMEFRAMES if any(x in str(row.get(f"{tf} H.A./MACD","")) for x in ["BEAR", "BAJISTA"]))
    bias_1d = str(row.get("1D MACD 0", ""))
    
    if bulls >= 5 and "SOBRE 0" in bias_1d: return "🔥 COMPRA FUERTE", "MTF CONFLUENCE BULL"
    if bears >= 5 and "BAJO 0" in bias_1d: return "🩸 VENTA FUERTE", "MTF CONFLUENCE BEAR"
    if "PULLBACK ALCISTA" in str(row.get("1m H.A./MACD", "")): return "💎 GIRO PROBABLE", "PULLBACK DETECTED"
    
    return "⚖️ RANGO", "NO TREND"

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
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
                    for c in ["H.A./MACD", "Hora Señal", "MACD 0", "Hist.", "Cruce MACD"]: row[f"{label} {c}"] = "-"
            v, e = get_verdict(row)
            row["VEREDICTO"] = v
            row["ESTRATEGIA"] = e
            results.append(row)
            time.sleep(0.05)
        except: continue
    prog.empty()
    return results

# ─────────────────────────────────────────────
# UI & STYLER
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V18.0")

def style_df(df):
    def apply_color(val):
        v = str(val).upper()
        # VERDE: BULL / SOBRE 0 / COMPRA
        if any(x in v for x in ["BULL", "SOBRE 0", "ALCISTA", "COMPRA", "RSI↑"]):
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        # ROJO: BEAR / BAJO 0 / VENTA
        if any(x in v for x in ["BEAR", "BAJO 0", "BAJISTA", "VENTA", "RSI↓"]):
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        # CELESTE: PULLBACK ALCISTA / GIRO / DETECTED
        if any(x in v for x in ["PULLBACK ALCISTA", "GIRO PROBABLE", "DETECTED"]):
            return 'background-color: #E1F5FE; color: #01579B; font-weight: bold;'
        # NARANJA: PULLBACK BAJISTA
        if "PULLBACK BAJISTA" in v:
            return 'background-color: #FFF3E0; color: #E65100; font-weight: bold;'
        return ''
    return df.style.applymap(apply_color)

with st.sidebar:
    st.header("Radar Control")
    all_sym = get_active_pairs()
    if all_sym:
        b_size = st.selectbox("Batch Size", [10, 20, 30], index=0)
        batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
        sel = st.selectbox("Select Batch", range(len(batches)))
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["sniper_results"] = scan_batch(batches[sel])

    st.divider()
    st.header("Filtros de Visibilidad")
    
    if st.session_state["sniper_results"]:
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        
        f_veredicto = st.multiselect("Filtrar Veredicto:", options=df_temp["VEREDICTO"].unique(), default=df_temp["VEREDICTO"].unique())
        f_estrategia = st.multiselect("Filtrar Estrategia:", options=df_temp["ESTRATEGIA"].unique(), default=df_temp["ESTRATEGIA"].unique())
    
    if st.button("Limpiar Todo"):
        st.session_state["sniper_results"] = []
        st.rerun()

# RENDERIZADO CON FILTROS
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Aplicar Filtros de Usuario
    df_final = df_final[df_final["VEREDICTO"].isin(f_veredicto) & df_final["ESTRATEGIA"].isin(f_estrategia)]
    
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df_final.columns]
    others = [c for c in df_final.columns if c not in valid]
    
    st.dataframe(style_df(df_final[valid + others]), use_container_width=True, height=800)
else:
    st.info("👈 Configure el lote y presione INICIAR ESCANEO.")
