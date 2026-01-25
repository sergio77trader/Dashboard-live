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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V25.0 (SLY STATE MACHINE)")

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

# ─────────────────────────────────────────────
# HEIKIN ASHI RECURSIVO (LÓGICA PINE)
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    
    df["HA_Close"] = ha_close
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

# ─────────────────────────────────────────────
# ANÁLISIS TÉCNICO (MÁQUINA DE ESTADOS SLY)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price, utc_offset=-3):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=250)
        if not ohlcv or len(ohlcv) < 201: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        
        # 1. Indicadores Base
        df["ema200"] = ta.ema(df["close"], length=200)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df = calculate_heikin_ashi(df)

        # --- 2. SIMULACIÓN DE MÁQUINA DE ESTADOS (ESTADO SLY) ---
        estado = 0
        entry_time = None
        
        # Recorremos el historial para determinar el estado actual
        for i in range(1, len(df)):
            hist = df["Hist"].iloc[i]
            prev_hist = df["Hist"].iloc[i-1]
            ha_color = df["HA_Color"].iloc[i]
            ema200 = df["ema200"].iloc[i]
            close = df["close"].iloc[i]
            
            # Salidas Dinámicas (Si MACD se da vuelta)
            if estado == 1 and hist < prev_hist:
                estado = 0
            elif estado == -1 and hist > prev_hist:
                estado = 0
            
            # Entradas (Solo si estamos FUERA)
            if estado == 0:
                long_cond = (ha_color == 1) and (hist > prev_hist) and (close > ema200)
                short_cond = (ha_color == -1) and (hist < prev_hist) and (close < ema200)
                
                if long_cond:
                    estado = 1
                    entry_time = df["dt"].iloc[i]
                elif short_cond:
                    estado = -1
                    entry_time = df["dt"].iloc[i]

        # --- 3. RESULTADOS FINALES ---
        txt_sig = "FUERA ⚪"
        icon = "⚪"
        if estado == 1:
            txt_sig = "LONG 🟢"
            icon = "🟢"
        elif estado == -1:
            txt_sig = "SHORT 🔴"
            icon = "🔴"
            
        signal_h = (entry_time + pd.Timedelta(hours=utc_offset)).strftime("%H:%M") if entry_time else "--:--"
        
        # Cruce MACD
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross = (crosses["dt"].iloc[-1] + pd.Timedelta(hours=utc_offset)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "signal": txt_sig,
            "signal_time": signal_h,
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJISTA",
            "cross_time": last_cross
        }
    except: return None

def get_verdict(row):
    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
    bias_1d = str(row.get("1D MACD 0", ""))
    if bulls >= 4 and "SOBRE 0" in bias_1d: return "🔥 COMPRA FUERTE", "MTF CONFLUENCE BULL"
    if bears >= 4 and "BAJO 0" in bias_1d: return "🩸 VENTA FUERTE", "MTF CONFLUENCE BEAR"
    return "⚖️ RANGO", "NO TREND"

# ─────────────────────────────────────────────
# MOTOR DE ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets, accumulate=True, utc_h=-3):
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
                res = analyze_ticker_tf(sym, tf, ex, p, utc_h)
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
        curr = {item["Activo"]: item for item in st.session_state["sniper_results"]}
        for item in new_results: curr[item["Activo"]] = item
        return list(curr.values())
    return new_results

# ─────────────────────────────────────────────
# UI & STYLER POR COLORES
# ─────────────────────────────────────────────
def get_color_category(val):
    v = str(val).upper()
    if "🟢" in v or "LONG" in v or "SOBRE 0" in v or "ALCISTA" in v: return "VERDE"
    if "🔴" in v or "SHORT" in v or "BAJO 0" in v or "BAJISTA" in v: return "ROJO"
    if "🔵" in v or "PULLBACK" in v: return "AZUL"
    return "BLANCO"

def style_df(df):
    def apply_color(val):
        cat = get_color_category(val)
        if cat == "VERDE": return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if cat == "ROJO": return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if cat == "AZUL": return 'background-color: #E1F5FE; color: #01579B; font-weight: bold;'
        if cat == "BLANCO": return 'background-color: #F5F5F5; color: #616161;'
        return ''
    return df.style.applymap(apply_color)

with st.sidebar:
    st.header("Radar Control SLY")
    utc_h = st.number_input("Diferencia Horaria (UTC)", value=-3)
    mode = st.radio("Modo:", ["Mercado", "Watchlist"])
    all_sym = get_active_pairs(min_volume=0)
    targets = []
    
    if mode == "Mercado":
        vol_min = st.number_input("Volumen Min.", value=100000, step=50000)
        f_sym = [s for s in all_sym if s in get_active_pairs(min_volume=vol_min)]
        st.success(f"Activos: {len(f_sym)}")
        b_size = st.selectbox("Batch", [20, 50, 100], index=1)
        batches = [f_sym[i:i+b_size] for i in range(0, len(f_sym), b_size)]
        sel = st.selectbox("Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
        targets = batches[sel] if batches else []
    else:
        targets = st.multiselect("Watchlist:", options=all_sym)

    mode_acc = st.checkbox("Acumular", value=True)
    if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
        if targets: st.session_state["sniper_results"] = scan_batch(targets, mode_acc, utc_h)

    if st.session_state["sniper_results"]:
        st.divider()
        st.header("Filtros de Color")
        color_opts = ["VERDE", "ROJO", "BLANCO"]
        f_colors = {}
        with st.expander("Filtrar TFs"):
            for label in TIMEFRAMES.keys():
                col_name = f"{label} H.A./MACD"
                f_colors[col_name] = st.multiselect(f"Color {label}:", options=color_opts, default=color_opts)
        f_v = st.multiselect("Veredicto:", options=color_opts, default=color_opts)

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# RENDERIZADO
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    # Aplicar filtros
    for col_n, sel_c in f_colors.items():
        if col_n in df_f.columns:
            df_f = df_f[df_f[col_n].apply(lambda x: get_color_category(x) in sel_c)]
    df_f = df_f[df_f["VEREDICTO"].apply(lambda x: get_color_category(x) in f_v)]
    
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df_f.columns]
    others = [c for c in df_f.columns if c not in valid]
    st.dataframe(style_df(df_f[valid + others]), use_container_width=True, height=800)
else:
    st.info("👈 Inicie escaneo.")
