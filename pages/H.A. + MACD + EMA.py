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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V25.0 (SLY ENGINE)")

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
def get_active_pairs(min_volume=100000):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume:
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
# ANÁLISIS TÉCNICO (ADAPTADO DE PINE SCRIPT SLY)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        # Pedimos 250 velas para asegurar el cálculo correcto de la EMA 200
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=250)
        if not ohlcv or len(ohlcv) < 200: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        
        # 1. MACD (12, 26, 9)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        
        # 2. EMA 200 (Filtro del primer script)
        df["ema200"] = ta.ema(df["close"], length=200)
        
        # 3. RSI 14
        df["RSI"] = ta.rsi(df["close"], length=14)
        
        # 4. Heikin Ashi
        df = calculate_heikin_ashi(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- LÓGICA DE GATILLO PINE SCRIPT SLY ---
        ha_verde = last["HA_Color"] == 1
        ha_rojo = last["HA_Color"] == -1
        hist_subiendo = last["Hist"] > prev["Hist"]
        hist_bajando = last["Hist"] < prev["Hist"]
        filtro_ema_long = last["close"] > last["ema200"]
        filtro_ema_short = last["close"] < last["ema200"]
        
        phase, icon = "NEUTRO", "⚪"
        
        # Lógica de entrada Long adaptada
        if ha_verde and hist_subiendo and filtro_ema_long:
            if last["Hist"] < 0:
                phase, icon = "PULLBACK ALCISTA", "🔵"
            else:
                phase, icon = "CONFIRMACION BULL", "🟢"
                
        # Lógica de entrada Short adaptada
        elif ha_rojo and hist_bajando and filtro_ema_short:
            if last["Hist"] > 0:
                phase, icon = "PULLBACK BAJISTA", "🟠"
            else:
                phase, icon = "CONFIRMACION BEAR", "🔴"

        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        
        # Hora del último cruce MACD
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        # Hora de la señal (Timestamp de la vela actual analizada)
        signal_time = (last["dt"] - pd.Timedelta(hours=3)).strftime("%H:%M")

        return {
            "signal": f"{icon} {phase} | {rsi_state} ({rsi_val})",
            "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if last["Hist"] > prev["Hist"] else "BAJISTA",
            "cross_time": last_cross,
            "signal_time": signal_time
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
# MOTOR DE ESCANEO
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
    return new_results

# ─────────────────────────────────────────────
# FUNCION MAPEO DE COLOR PARA FILTRO
# ─────────────────────────────────────────────
def get_color_category(val):
    v = str(val).upper()
    if any(x in v for x in ["BULL", "SOBRE 0", "ALCISTA", "COMPRA"]): return "VERDE"
    if any(x in v for x in ["BEAR", "BAJO 0", "BAJISTA", "VENTA"]): return "ROJO"
    if any(x in v for x in ["PULLBACK ALCISTA", "GIRO PROBABLE", "DETECTED"]): return "AZUL"
    if "PULLBACK BAJISTA" in v: return "NARANJA"
    return "BLANCO"

# ─────────────────────────────────────────────
# UI & STYLER
# ─────────────────────────────────────────────
def style_df(df):
    def apply_color(val):
        cat = get_color_category(val)
        if cat == "VERDE": return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if cat == "ROJO": return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if cat == "AZUL": return 'background-color: #E1F5FE; color: #01579B; font-weight: bold;'
        if cat == "NARANJA": return 'background-color: #FFF3E0; color: #E65100; font-weight: bold;'
        if cat == "BLANCO": return 'background-color: #F5F5F5; color: #616161; font-weight: normal;'
        return ''
    return df.style.applymap(apply_color)

with st.sidebar:
    st.header("Radar Control")
    mode = st.radio("Modo:", ["Mercado", "Watchlist"])
    all_sym = get_active_pairs(min_volume=0)
    targets = []
    
    if mode == "Mercado":
        vol_min = st.number_input("Volumen Min.", value=100000, step=50000)
        f_sym = [s for s in all_sym if s in get_active_pairs(min_volume=vol_min)]
        st.success(f"Disponibles: {len(f_sym)}")
        b_size = st.selectbox("Batch", [20, 50, 100], index=1)
        batches = [f_sym[i:i+b_size] for i in range(0, len(f_sym), b_size)]
        sel = st.selectbox("Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
        targets = batches[sel] if batches else []
    else:
        targets = st.multiselect("Watchlist:", options=all_sym)

    mode_acc = st.checkbox("Acumular", value=True)
    if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
        if targets: st.session_state["sniper_results"] = scan_batch(targets, accumulate=mode_acc)

    st.divider()
    if st.session_state["sniper_results"]:
        st.header("Filtros por Colores")
        color_options = ["VERDE", "ROJO", "AZUL", "NARANJA", "BLANCO"]
        f_colors = {}
        with st.expander("Filtrar por H.A./MACD"):
            for label in TIMEFRAMES.keys():
                col_name = f"{label} H.A./MACD"
                f_colors[col_name] = st.multiselect(f"Color {label}:", options=color_options, default=color_options)
        
        st.header("Filtros Core")
        f_v = st.multiselect("Veredicto:", options=color_options, default=color_options)

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# RENDERIZADO
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    for col_name, selected_colors in f_colors.items():
        if col_name in df_f.columns:
            df_f = df_f[df_f[col_name].apply(lambda x: get_color_category(x) in selected_colors)]
    df_f = df_f[df_f["VEREDICTO"].apply(lambda x: get_color_category(x) in f_v)]
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df_f.columns]
    others = [c for c in df_f.columns if c not in valid]
    st.dataframe(style_df(df_f[valid + others]), use_container_width=True, height=800)
else:
    st.info("👈 Presione INICIAR ESCANEO.")
