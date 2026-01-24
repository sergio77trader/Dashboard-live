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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V21.0")

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
# MOTOR DE DATOS (FILTRO RELAJADO PARA MÁS ACTIVOS)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_pairs(min_volume=100000): # Bajamos de 1M a 100k para captar +500 activos
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            # Filtro USDT Futures y volumen mínimo (relajado)
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        
        df_v = pd.DataFrame(valid).sort_values("vol", ascending=False)
        return df_v["symbol"].tolist()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return []

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

        last, prev = df.iloc[-1], df.iloc[-2]
        phase, icon = "NEUTRO", "⚪"
        if last["HA_Color"] == 1 and last["Hist"] > prev["Hist"]:
            phase, icon = ("PULLBACK ALCISTA", "🔵") if last["Hist"] < 0 else ("CONFIRMACION BULL", "🟢")
        elif last["HA_Color"] == -1 and last["Hist"] < prev["Hist"]:
            phase, icon = ("PULLBACK BAJISTA", "🟠") if last["Hist"] > 0 else ("CONFIRMACION BEAR", "🔴")

        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "signal": f"{icon} {phase} | {rsi_state} ({rsi_val})",
            "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if last["Hist"] > prev["Hist"] else "BAJISTA",
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
# ESCANEO ACUMULATIVO
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
                    for c in ["H.A./MACD", "Hora Señal", "MACD 0", "Hist.", "Cruce MACD"]: row[f"{label} {c}"] = "-"
            v, e = get_verdict(row)
            row["VEREDICTO"] = v
            row["ESTRATEGIA"] = e
            new_results.append(row)
            time.sleep(0.05)
        except: continue
    prog.empty()

    if accumulate:
        current_data = {item["Activo"]: item for item in st.session_state["sniper_results"]}
        for item in new_results: current_data[item["Activo"]] = item
        return list(current_data.values())
    else: return new_results

# ─────────────────────────────────────────────
# UI & STYLER
# ─────────────────────────────────────────────
def style_df(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["BULL", "SOBRE 0", "ALCISTA", "COMPRA", "RSI↑"]): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if any(x in v for x in ["BEAR", "BAJO 0", "BAJISTA", "VENTA", "RSI↓"]): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if any(x in v for x in ["PULLBACK ALCISTA", "GIRO PROBABLE", "DETECTED"]): return 'background-color: #E1F5FE; color: #01579B; font-weight: bold;'
        if "PULLBACK BAJISTA" in v: return 'background-color: #FFF3E0; color: #E65100; font-weight: bold;'
        if any(x in v for x in ["RANGO", "NO TREND"]): return 'background-color: #F5F5F5; color: #616161; font-weight: normal;'
        return ''
    return df.style.applymap(apply_color)

with st.sidebar:
    st.header("Radar Control")
    
    # Selector de volumen dinámico
    vol_min = st.number_input("Volumen Mínimo (24h)", value=100000, step=50000)
    
    all_sym = get_active_pairs(min_volume=vol_min)
    
    if all_sym:
        st.success(f"Activos encontrados: {len(all_sym)}")
        b_size = st.selectbox("Batch Size", [10, 20, 30, 50, 100], index=3)
        batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
        
        # Selector de Lote más descriptivo
        batch_options = {i: f"Lote {i} ({len(batches[i])} activos)" for i in range(len(batches))}
        sel = st.selectbox("Select Batch", options=list(batch_options.keys()), format_func=lambda x: batch_options[x])
        
        mode_acc = st.checkbox("Acumular Resultados", value=True)
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["sniper_results"] = scan_batch(batches[sel], accumulate=mode_acc)

    st.divider()
    if st.session_state["sniper_results"]:
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        f_ver = st.multiselect("Filtrar Veredicto:", options=df_temp["VEREDICTO"].unique(), default=df_temp["VEREDICTO"].unique())
        f_est = st.multiselect("Filtrar Estrategia:", options=df_temp["ESTRATEGIA"].unique(), default=df_temp["ESTRATEGIA"].unique())
    
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# RENDER
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    df_final = df_final[df_final["VEREDICTO"].isin(f_ver) & df_final["ESTRATEGIA"].isin(f_est)]
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df_final.columns]
    others = [c for c in df_final.columns if c not in valid]
    st.dataframe(style_df(df_final[valid + others]), use_container_width=True, height=800)
else:
    st.info("👈 Presione INICIAR ESCANEO.")
