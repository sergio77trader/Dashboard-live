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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER V27.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { 
        border: 2px solid #2962FF !important; 
        border-radius: 8px !important;
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
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})
    ex.load_markets()
    return ex

@st.cache_data(ttl=300)
def get_all_symbols():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s in tickers if "/USDT:USDT" in s]
    except: return []

@st.cache_data(ttl=300)
def get_active_pairs_by_vol(min_vol):
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
        
        hist = macd["MACDh_12_26_9"]
        macd_line = macd["MACD_12_26_9"]
        signal_line = macd["MACDs_12_26_9"]
        
        df["Hist"], df["MACD"], df["Signal"] = hist, macd_line, signal_line
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
        
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        cross_rows = df[df["cross"]]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            cross_result = "Alcista" if last_cross["MACD"] > last_cross["Signal"] else "Bajista"
        else: cross_result = "--"

        return {
            "signal": f"{'🟢' if position=='LONG' else '🔴' if position=='SHORT' else '⚪'} {position} | {rsi_state}",
            "signal_time": (last_date - pd.Timedelta(hours=3)).strftime("%H:%M"),
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h_dir": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "cross_state": cross_result,
            # Data cruda para lógica multitemporal
            "raw_hist": df["Hist"].iloc[-1],
            "raw_prev_hist": df["Hist"].iloc[-2],
            "raw_macd": df["MACD"].iloc[-1],
            "raw_signal": df["Signal"].iloc[-1]
        }
    except: return None

# ─────────────────────────────────────────────
# NUEVA LÓGICA: IMPULSO MULTITEMPORAL
# ─────────────────────────────────────────────
def get_impulse_strategy(row):
    try:
        # 1. Sesgo (High TFs: 1D, 4H)
        bias_1d = row.get("1D_data")
        bias_4h = row.get("4H_data")
        
        is_bull_bias = False
        is_bear_bias = False
        
        if bias_1d and bias_4h:
            # Sesgo Alcista: Hist > 0 + Expansión + MACD > Signal
            if (bias_1d['raw_hist'] > 0 and bias_1d['raw_hist'] > bias_1d['raw_prev_hist'] and bias_1d['raw_macd'] > bias_1d['raw_signal']):
                is_bull_bias = True
            # Sesgo Bajista: Hist < 0 + Expansión + MACD < Signal
            elif (bias_1d['raw_hist'] < 0 and bias_1d['raw_hist'] < bias_1d['raw_prev_hist'] and bias_1d['raw_macd'] < bias_1d['raw_signal']):
                is_bear_bias = True

        # 2. Gatillo (Low TFs: 15m, 1m)
        trigger_15m = row.get("15m_data")
        trigger_1m = row.get("1m_data")
        
        if is_bull_bias and trigger_15m:
            # Hist pasa neg->pos O expansión positiva + Cruce Alcista
            if (trigger_15m['raw_hist'] > trigger_15m['raw_prev_hist']) and trigger_15m['cross_state'] == "Alcista":
                return "🚀 COMPRA (IMPULSO)"
        
        if is_bear_bias and trigger_15m:
            # Hist pasa pos->neg O expansión negativa + Cruce Bajista
            if (trigger_15m['raw_hist'] < trigger_15m['raw_prev_hist']) and trigger_15m['cross_state'] == "Bajista":
                return "🩸 VENTA (IMPULSO)"
                
        # 3. Contexto (Medium TFs: 1H, 30m) - Pullbacks
        context_1h = row.get("1H_data")
        if is_bull_bias and context_1h:
            if context_1h['raw_hist'] < context_1h['raw_prev_hist']:
                return "🔄 PULLBACK ALCISTA"
        if is_bear_bias and context_1h:
            if context_1h['raw_hist'] > context_1h['raw_prev_hist']:
                return "🔄 PULLBACK BAJISTA"

        return "⚖️ SIN IMPULSO"
    except: return "Error"

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
    new_results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym.split(':')[0]}")
        try:
            p = ex.fetch_ticker(sym)["last"]
            row = {"Activo": sym.split(":")[0].replace("/USDT", ""), "Precio": f"{p:,.4f}"}
            
            # Contenedores temporales para la nueva lógica multitemporal
            tf_raw_data = {}

            for label, tf in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf, ex, p)
                if res:
                    row[f"{label} H.A./MACD"], row[f"{label} Hora Señal"] = res["signal"], res["signal_time"]
                    row[f"{label} MACD 0"], row[f"{label} Hist."], row[f"{label} Cruce MACD"] = res["m0"], res["h_dir"], res["cross_state"]
                    tf_raw_data[f"{label}_data"] = res
                else:
                    for c in ["H.A./MACD","Hora Señal","MACD 0","Hist.","Cruce MACD"]: row[f"{label} {c}"] = "-"
            
            # Inyectar data cruda en row temporalmente para la función de impulso
            row.update(tf_raw_data)
            
            row["VEREDICTO"], row["ESTRATEGIA"] = get_verdict(row)
            row["MACD REC."] = get_macd_rec(row)
            row["IMPULSO MULTITEMPORAL"] = get_impulse_strategy(row)
            
            # Limpiar data cruda antes de guardar en resultados
            final_row = {k: v for k, v in row.items() if "_data" not in k}
            new_results.append(final_row)
            time.sleep(0.05)
        except: continue
    prog.empty()
    if acc:
        curr = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in new_results: curr[r["Activo"]] = r
        return list(curr.values())
    return new_results

def style_matrix(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA", "ALCISTA", "IMPULSO"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA", "BAJISTA"]): return 'background-color: #f8d7da; color: #721c24;'
        if any(x in v for x in ["GIRO", "PULLBACK"]): return 'background-color: #fff3cd; color: #856404;'
        return ''
    return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Radar Control")
    analysis_mode = st.radio("Modo de Análisis:", ["Mercado (Lotes)", "Watchlist (Manual)"])
    targets_to_scan = []
    if analysis_mode == "Mercado (Lotes)":
        min_volume = st.number_input("Volumen Mínimo 24h (USDT):", value=500000, step=100000)
        all_sym = get_active_pairs_by_vol(min_volume)
        if all_sym:
            b_size = st.selectbox("Lote de escaneo:", [10, 20, 50], index=1)
            batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
            sel_lote = st.selectbox("Seleccionar Lote:", range(len(batches)))
            targets_to_scan = batches[sel_lote]
    else:
        full_list = get_all_symbols()
        targets_to_scan = st.multiselect("Seleccionar Activos:", options=full_list)

    acc = st.checkbox("Acumular Resultados", value=True)
    if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
        if targets_to_scan: st.session_state["sniper_results"] = scan_batch(targets_to_scan, acc)

    st.divider()
    if st.session_state["sniper_results"]:
        st.subheader("🧹 Post-Filtros")
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        f_imp = st.multiselect("Impulso:", options=df_temp["IMPULSO MULTITEMPORAL"].unique(), default=df_temp["IMPULSO MULTITEMPORAL"].unique())
        f_ver = st.multiselect("Veredicto:", options=df_temp["VEREDICTO"].unique(), default=df_temp["VEREDICTO"].unique())
    
    if st.button("Limpiar Memoria"): st.session_state["sniper_results"] = []; st.rerun()

# MANUAL
with st.expander("📘 MANUAL OPERATIVO V27"):
    st.markdown("""
    ### 📌 IMPULSO MULTITEMPORAL
    *   **🚀 COMPRA (IMPULSO):** Sesgo 1D/4H Alcista + Expansión en 15m + Cruce Alcista.
    *   **🩸 VENTA (IMPULSO):** Sesgo 1D/4H Bajista + Expansión en 15m + Cruce Bajista.
    *   **🔄 PULLBACK:** Sesgo a favor, pero el momentum medio (1H) está contrayéndose.
    """)

# RENDERIZADO
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    df_f = df_f[df_f["IMPULSO MULTITEMPORAL"].isin(f_imp) & df_f["VEREDICTO"].isin(f_ver)]
    prio = ["Activo", "IMPULSO MULTITEMPORAL", "VEREDICTO", "ESTRATEGIA", "Precio"]
    df_f = df_f[prio + [c for c in df_f.columns if c not in prio]]
    st.dataframe(style_matrix(df_f), use_container_width=True, height=800)
else: st.info("👈 Inicie el radar para capturar impulsos.")
