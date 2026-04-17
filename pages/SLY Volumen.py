import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | VOLUME & MOMENTUM ENGINE")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #00E676; padding-bottom: 10px; }
    .stDataFrame { background-color: white; border-radius: 10px; border: 1px solid #DDD; }
</style>
""", unsafe_allow_html=True)

if "persistent_list" not in st.session_state:
    st.session_state["persistent_list"] = []
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []
if "ptr" not in st.session_state:
    st.session_state["ptr"] = 0

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 30000})

def fetch_universe(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = [s for s, t in tickers.items() if "/USDT" in s and (t.get('quoteVolume') or 0) >= min_vol]
        return sorted(valid)
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_indicators(df):
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    
    return {
        "Histograma": "SUBIENDO 📈" if hist.iloc[-1] > hist.iloc[-2] else "BAJANDO 📉",
        "Cruce MACD": "ALCISTA 🟢" if macd_line.iloc[-1] > signal_line.iloc[-1] else "BAJISTA 🔴",
        "Vela HA": "VERDE 🟢" if ha_close.iloc[-1] > ha_open[-1] else "ROJA 🔴"
    }

def get_verdict(v2, v4, v21, indicators):
    if v2 > 150 and indicators["Vela HA"] == "VERDE 🟢" and indicators["Histograma"] == "SUBIENDO 📈":
        return "🔥 COMPRA INMINENTE", "Volumen explosivo con dirección."
    if v21 > 60 and indicators["Vela HA"] == "VERDE 🟢":
        return "🐳 ACUMULACIÓN PRO", "Manos fuertes comprando."
    if v2 > 150 and indicators["Vela HA"] == "ROJA 🔴":
        return "🩸 VENTA AGRESIVA", "Distribución masiva."
    return "⚖️ NEUTRAL", "Sin desequilibrio."

def analyze_asset(symbol, tf, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'open', 'high', 'low', 'close', 'v'])
        tech = calculate_indicators(df)
        
        # Inicialización completa del diccionario para asegurar existencia de llaves
        res = {
            "Activo": symbol.replace("/USDT", ""),
            "RECOMENDACIÓN": "",
            "HA": tech["Vela HA"],
            "MACD Hist": tech["Histograma"],
            "MACD Cross": tech["Cruce MACD"],
            "Precio": f"{df['close'].iloc[-1]:,.4f}"
        }
        
        for p in [2, 4, 21, 42]:
            curr = df['v'].tail(p).sum()
            prev = df['v'].iloc[-(p*2):-p].sum()
            chg = ((curr - prev) / prev * 100) if prev > 0 else 0
            res[f"Chg {p}v (%)"] = round(chg, 2)
            
        res["RECOMENDACIÓN"], res["Análisis"] = get_verdict(res["Chg {2}v (%)".format(2)], 0, 0, tech) # Fix temporal de acceso
        # Re-asignación correcta
        v2 = res["Chg 2v (%)"]
        v4 = res["Chg 4v (%)"]
        v21 = res["Chg 21v (%)"]
        res["RECOMENDACIÓN"], res["Análisis"] = get_verdict(v2, v4, v21, tech)
        
        return res
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY - CONFLUENCE & VOLUME TERMINAL")

with st.sidebar:
    st.header("⚙️ Configuración")
    min_vol = st.number_input("Volumen Mínimo (USDT)", value=1000000)
    tf = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
    
    if st.button("📡 1. CARGAR MERCADO"):
        st.session_state["all_symbols"] = fetch_universe(min_vol)
        st.session_state["ptr"] = 0
        st.rerun()

    if st.session_state["all_symbols"]:
        ptr = st.session_state["ptr"]
        batch_size = st.slider("Activos por lote", 10, 100, 30)
        
        if ptr < len(st.session_state["all_symbols"]):
            if st.button(f"🚀 ANALIZAR LOTE: {ptr} a {min(ptr+batch_size, len(st.session_state['all_symbols']))}", type="primary"):
                ex = get_exchange()
                targets = st.session_state["all_symbols"][ptr : ptr+batch_size]
                prog = st.progress(0)
                for i, sym in enumerate(targets):
                    res = analyze_asset(sym, tf, ex)
                    if res: st.session_state["persistent_list"].append(res)
                    prog.progress((i+1)/len(targets))
                st.session_state["ptr"] += batch_size
                st.rerun()

    if st.button("🗑️ LIMPIAR TODO"):
        st.session_state["persistent_list"] = []
        st.session_state["ptr"] = 0
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO FINAL (FIX DE COLUMNAS)
# ─────────────────────────────────────────────
if st.session_state["persistent_list"]:
    df_raw = pd.DataFrame(st.session_state["persistent_list"])
    df_accumulated = df_raw.drop_duplicates(subset="Activo", keep="last")
    
    # ORDEN DE COLUMNAS SEGURO (Solo si existen)
    desired_prio = ["Activo", "RECOMENDACIÓN", "HA", "MACD Hist", "MACD Cross", "Precio"]
    actual_cols = df_accumulated.columns.tolist()
    
    # Construir lista de columnas final basada en lo que realmente existe
    ordered_cols = [c for c in desired_prio if c in actual_cols]
    remaining = [c for c in actual_cols if c not in ordered_cols and c != "Análisis"]
    final_col_list = ordered_cols + remaining + ([ "Análisis" ] if "Análisis" in actual_cols else [])

    df_final = df_accumulated[final_col_list].sort_values(by="Chg 2v (%)", ascending=False)

    def style_rows(val):
        try:
            v = str(val)
            if any(x in v for x in ["VERDE", "SUBIENDO", "ALCISTA", "COMPRA"]): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if any(x in v for x in ["ROJA", "BAJANDO", "BAJISTA", "VENTA"]): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
            if isinstance(val, (int, float)) and val > 100: return 'color: #1B5E20; font-weight: bold;'
        except: pass
        return ''

    st.dataframe(df_final.style.map(style_rows), use_container_width=True, height=600)
    st.download_button("📥 Reporte", df_final.to_csv(index=False), "sly_data.csv")
else:
    st.info("👈 Configure y analice un lote.")
