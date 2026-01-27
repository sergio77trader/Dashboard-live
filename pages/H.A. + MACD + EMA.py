import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V25.5")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { 
        border: 2px solid #2962FF !important; 
        border-radius: 8px !important;
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m":"1m", "5m":"5m", "15m":"15m",
    "30m":"30m", "1H":"1h", "4H":"4h", "1D":"1d"
}

# ─────────────────────────────────────────────
# MANUAL OPERATIVO
# ─────────────────────────────────────────────
with st.expander("📘 MANUAL OPERATIVO Y FILTROS"):
    st.info("Referencia de métricas y confluencias institucionales.")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("""
        ### 🎯 LÓGICA DE MANDO
        *   **VEREDICTO:** Orden ejecutiva basada en confluencia masiva + Sesgo 1D.
        *   **ESTRATEGIA:** Fase técnica detectada (Sync, Recovery, Correction).
        *   **MACD REC.:** Momentum de bloques intermedios (15m, 1H, 4H).
        """)
    with col_m2:
        st.markdown("""
        ### 📊 FILTROS DE MERCADO
        *   **Volumen Mínimo:** Solo analiza activos con capitalización de flujo real (USDT).
        *   **Post-Filtro:** Permite aislar oportunidades sin distracciones una vez terminado el escaneo.
        """)

# ─────────────────────────────────────────────
# MOTOR DE DATOS CON FILTRO DE VOLUMEN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})
    ex.load_markets()
    return ex

@st.cache_data(ttl=300)
def get_active_pairs(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_vol:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"], df["HA_Color"] = ha_open, np.where(df["HA_Close"] > ha_open, 1, -1)
    return df

def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")
        macd = ta.macd(df["close"])
        df["Hist"], df["MACD"], df["Signal"] = macd["MACDh_12_26_9"], macd["MACD_12_26_9"], macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        position, last_date = "NEUTRO", df["dt"].iloc[-1]
        for i in range(1, len(df)):
            h, ph, hc, d = df["Hist"].iloc[i], df["Hist"].iloc[i-1], df["HA_Color"].iloc[i], df["dt"].iloc[i]
            if position == "LONG" and h < ph: position = "NEUTRO"
            elif position == "SHORT" and h > ph: position = "NEUTRO"
            if position == "NEUTRO":
                if hc == 1 and h > ph: position, last_date = "LONG", d
                elif hc == -1 and h < ph: position, last_date = "SHORT", d

        rsi_val = round(df["RSI"].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        
        # LÓGICA DE CRUCE DIRECCIONAL (Alcista/Bajista)
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        cross_rows = df[df["cross"]]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            cross_result = "Alcista" if last_cross["MACD"] > last_cross["Signal"] else "Bajista"
        else:
            cross_result = "--"

        return {
            "signal": f"{'🟢' if position=='LONG' else '🔴' if position=='SHORT' else '⚪'} {position} | {rsi_state}",
            "signal_time": (last_date - pd.Timedelta(hours=3)).strftime("%H:%M"),
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h_dir": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "cross_state": cross_result
        }
    except: return None

def get_verdict(row):
    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
    bias_1d = str(row.get("1D MACD 0", ""))
    micro_bull = all("LONG" in str(row.get(f"{tf} H.A./MACD","")) for tf in ["1m", "5m", "15m"])
    micro_bear = all("SHORT" in str(row.get(f"{tf} H.A./MACD","")) for tf in ["1m", "5m", "15m"])

    if bulls >= 5 and "SOBRE 0" in bias_1d: return "🔥 COMPRA FUERTE", "MTF BULLISH SYNC"
    if bears >= 5 and "BAJO 0" in bias_1d: return "🩸 VENTA FUERTE", "MTF BEARISH SYNC"
    if micro_bull and "BAJO 0" in bias_1d: return "💎 GIRO/REBOTE", "FAST RECOVERY"
    if micro_bear and "SOBRE 0" in bias_1d: return "📉 RETROCESO", "CORRECTION START"
    return "⚖️ RANGO", "NO TREND"

def get_macd_rec(row):
    sub = sum(1 for tf in ["15m", "1H", "4H"] if "SUBIENDO" in str(row.get(f"{tf} Hist.", "")))
    return "📈 MOMENTUM ALCISTA" if sub >= 2 else "📉 MOMENTUM BAJISTA"

# ─────────────────────────────────────────────
# MOTOR DE ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets, acc):
    ex = get_exchange()
    results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym.split(':')[0]}")
        try:
            p = ex.fetch_ticker(sym)["last"]
            row = {"Activo": sym.split(":")[0].replace("/USDT", ""), "Precio": f"{p:,.4f}"}
            for label, tf in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf, ex, p)
                if res:
                    row[f"{label} H.A./MACD"], row[f"{label} Hora Señal"] = res["signal"], res["signal_time"]
                    row[f"{label} MACD 0"], row[f"{label} Hist."], row[f"{label} Cruce MACD"] = res["m0"], res["h_dir"], res["cross_state"]
                else:
                    for c in ["H.A./MACD","Hora Señal","MACD 0","Hist.","Cruce MACD"]: row[f"{label} {c}"] = "-"
            row["VEREDICTO"], row["ESTRATEGIA"] = get_verdict(row)
            row["MACD REC."] = get_macd_rec(row)
            results.append(row)
            time.sleep(0.05)
        except: continue
    prog.empty()
    if acc:
        curr = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in results: curr[r["Activo"]] = r
        return list(curr.values())
    return results

def style_matrix(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA", "ALCISTA"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA", "BAJISTA"]): return 'background-color: #f8d7da; color: #721c24;'
        if "GIRO" in v: return 'background-color: #fff3cd; color: #856404;'
        return ''
    return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Radar Control")
    min_volume = st.number_input("Volumen Mínimo 24h (USDT):", value=500000, step=100000)
    all_sym = get_active_pairs(min_volume)
    
    if all_sym:
        st.success(f"Activos filtrados: {len(all_pairs := all_sym)}")
        b_size = st.selectbox("Lote de escaneo:", [10, 20, 50], index=1)
        batches = [all_pairs[i:i+b_size] for i in range(0, len(all_pairs), b_size)]
        sel = st.selectbox("Seleccionar Lote:", range(len(batches)))
        acc = st.checkbox("Acumular Resultados", value=True)
        if st.button("🚀 INICIAR ESCANEO", type="primary"):
            st.session_state["sniper_results"] = scan_batch(batches[sel], acc)
    
    st.divider()
    if st.session_state["sniper_results"]:
        st.subheader("🧹 Post-Filtros de Tabla")
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        f_ver = st.multiselect("Veredicto:", options=df_temp["VEREDICTO"].unique(), default=df_temp["VEREDICTO"].unique())
        f_est = st.multiselect("Estrategia:", options=df_temp["ESTRATEGIA"].unique(), default=df_temp["ESTRATEGIA"].unique())
        f_mac = st.multiselect("MACD Rec.:", options=df_temp["MACD REC."].unique(), default=df_temp["MACD REC."].unique())
    
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    # Aplicar Post-Filtros
    df_f = df_f[df_f["VEREDICTO"].isin(f_ver) & df_f["ESTRATEGIA"].isin(f_est) & df_f["MACD REC."].isin(f_mac)]
    
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "MACD REC.", "Precio"]
    df_f = df_f[prio + [c for c in df_f.columns if c not in prio]]
    st.dataframe(style_matrix(df_f), use_container_width=True, height=800)
else:
    st.info("👈 Ajuste el volumen y seleccione un lote para iniciar.")
