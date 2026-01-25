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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V26.0")

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
def get_active_pairs(min_volume=50000): # Bajamos filtro para ver más activos
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
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = np.zeros(len(df))
    # Inicialización exacta como Pine Script
    ha_open[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    df["HA_Close"] = ha_close
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

# ─────────────────────────────────────────────
# ANÁLISIS TÉCNICO (MÁQUINA DE ESTADOS REFORZADA)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price, utc_offset=-3):
    try:
        # Pedimos 500 velas para que la EMA 200 tenga 300 velas de cálculo sólido
        limit = 500
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit)
        if not ohlcv or len(ohlcv) < 50: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        
        # 1. Indicadores (Lógica Estricta)
        df["ema200"] = ta.ema(df["close"], length=200)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        # 2. Simulación de Estados SLY
        estado = 0
        entry_time = None
        
        # Empezamos desde la vela 200 para asegurar que EMA200 existe
        start_idx = 200 if len(df) > 200 else 1
        
        for i in range(start_idx, len(df)):
            hist = df["Hist"].iloc[i]
            prev_hist = df["Hist"].iloc[i-1]
            ha_color = df["HA_Color"].iloc[i]
            ema200 = df["ema200"].iloc[i]
            close = df["close"].iloc[i]
            
            # Si EMA es NaN, no podemos operar (Sincronía con TV)
            if np.isnan(ema200): continue

            # Salidas Dinámicas
            if estado == 1 and hist < prev_hist: estado = 0
            elif estado == -1 and hist > prev_hist: estado = 0
            
            # Entradas
            if estado == 0:
                if ha_color == 1 and hist > prev_hist and close > ema200:
                    estado = 1
                    entry_time = df["dt"].iloc[i]
                elif ha_color == -1 and hist < prev_hist and close < ema200:
                    estado = -1
                    entry_time = df["dt"].iloc[i]

        # 3. Datos de Salida
        last_macd = df["MACD"].iloc[-1]
        last_hist = df["Hist"].iloc[-1]
        prev_hist = df["Hist"].iloc[-2]
        rsi_val = round(df["RSI"].iloc[-1], 1)
        
        txt_sig = "FUERA ⚪"
        if estado == 1: txt_sig = f"LONG 🟢 | RSI {rsi_val}"
        elif estado == -1: txt_sig = f"SHORT 🔴 | RSI {rsi_val}"
        else: txt_sig = f"FUERA ⚪ | RSI {rsi_val}"
            
        signal_h = (entry_time + pd.Timedelta(hours=utc_offset)).strftime("%H:%M") if entry_time else "--:--"
        
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross = (crosses["dt"].iloc[-1] + pd.Timedelta(hours=utc_offset)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "signal": txt_sig,
            "signal_time": signal_h,
            "m0": "SOBRE 0" if last_macd > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if last_hist > prev_hist else "BAJISTA",
            "cross_time": last_cross
        }
    except Exception as e:
        return None

def get_verdict(row):
    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
    if bulls >= 4: return "🔥 COMPRA FUERTE", "MTF BULLISH"
    if bears >= 4: return "🩸 VENTA FUERTE", "MTF BEARISH"
    return "⚖️ RANGO", "NO TREND"

# ─────────────────────────────────────────────
# ESCANEO
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
                    for c in ["H.A./MACD", "Hora Señal", "MACD 0", "Hist.", "Cruce MACD"]: row[f"{label} {c}"] = "S/D"
            v, e = get_verdict(row)
            row["VEREDICTO"] = v
            row["ESTRATEGIA"] = e
            new_results.append(row)
            time.sleep(0.1) # Mayor estabilidad para KuCoin
        except: continue
    prog.empty()
    if accumulate:
        curr = {item["Activo"]: item for item in st.session_state["sniper_results"]}
        for item in new_results: curr[item["Activo"]] = item
        return list(curr.values())
    return new_results

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
def get_color_category(val):
    v = str(val).upper()
    if "🟢" in v or "LONG" in v or "SOBRE" in v or "ALCISTA" in v: return "VERDE"
    if "🔴" in v or "SHORT" in v or "BAJO" in v or "BAJISTA" in v: return "ROJO"
    return "BLANCO"

def style_df(df):
    def apply_color(val):
        cat = get_color_category(val)
        if cat == "VERDE": return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if cat == "ROJO": return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        return ''
    return df.style.applymap(apply_color)

with st.sidebar:
    st.header("Radar SLY V26")
    utc_h = st.number_input("UTC", value=-3)
    mode = st.radio("Modo:", ["Mercado", "Watchlist"])
    all_sym = get_active_pairs()
    
    if mode == "Mercado":
        vol_min = st.number_input("Volumen Min.", value=50000)
        f_sym = [s for s in all_sym if s in get_active_pairs(min_volume=vol_min)]
        st.success(f"Activos: {len(f_sym)}")
        sel_batch = st.selectbox("Lote (50)", range(0, len(f_sym), 50), format_func=lambda x: f"Activos {x} al {x+50}")
        targets = f_sym[sel_batch : sel_batch+50]
    else:
        targets = st.multiselect("Watchlist:", options=all_sym)

    if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
        st.session_state["sniper_results"] = scan_batch(targets, True, utc_h)
    
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    valid = [c for c in prio if c in df_f.columns]
    others = [c for c in df_f.columns if c not in valid]
    st.dataframe(style_df(df_f[valid + others]), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione activos y ejecute escaneo.")
