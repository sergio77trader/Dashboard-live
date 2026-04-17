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
    .metric-box { padding: 15px; border-radius: 10px; background: white; border: 1px solid #eee; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA BLINDADA ---
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
# CÁLCULOS TÉCNICOS (MACD & HEIKIN ASHI)
# ─────────────────────────────────────────────
def calculate_indicators(df):
    # 1. MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    
    # 2. Heikin Ashi Recursivo
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    
    # Estados actuales
    hist_now = hist.iloc[-1]
    hist_prev = hist.iloc[-2]
    macd_now = macd_line.iloc[-1]
    signal_now = signal_line.iloc[-1]
    ha_o_now = ha_open[-1]
    ha_c_now = ha_close.iloc[-1]
    
    return {
        "Histograma": "SUBIENDO 📈" if hist_now > hist_prev else "BAJANDO 📉",
        "Cruce MACD": "ALCISTA 🟢" if macd_now > signal_now else "BAJISTA 🔴",
        "Vela HA": "VERDE 🟢" if ha_c_now > ha_o_now else "ROJA 🔴"
    }

# ─────────────────────────────────────────────
# LÓGICA DE RECOMENDACIÓN
# ─────────────────────────────────────────────
def get_verdict(v2, v4, v21, indicators):
    # Una recomendación profesional exige volumen + dirección
    if v2 > 150 and indicators["Vela HA"] == "VERDE 🟢" and indicators["Histograma"] == "SUBIENDO 📈":
        return "🔥 COMPRA INMINENTE", "Volumen explosivo con dirección confirmada."
    if v21 > 60 and indicators["Vela HA"] == "VERDE 🟢":
        return "🐳 ACUMULACIÓN PRO", "Manos fuertes comprando sostenidamente."
    if v2 > 150 and indicators["Vela HA"] == "ROJA 🔴":
        return "🩸 VENTA AGRESIVA", "Distribución masiva detectada."
    return "⚖️ NEUTRAL", "Sin desequilibrio claro."

def analyze_asset(symbol, tf, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'open', 'high', 'low', 'close', 'v'])
        
        # Obtener indicadores de confluencia
        tech = calculate_indicators(df)
        
        res = {
            "Activo": symbol.replace("/USDT", ""),
            "Precio": f"{df['close'].iloc[-1]:,.4f}",
            "HA": tech["Vela HA"],
            "MACD Hist": tech["Histograma"],
            "MACD Cross": tech["Cruce MACD"]
        }
        
        for p in [2, 4, 21, 42]:
            curr = df['v'].tail(p).sum()
            prev = df['v'].iloc[-(p*2):-p].sum()
            chg = ((curr - prev) / prev * 100) if prev > 0 else 0
            res[f"Chg {p}v (%)"] = round(chg, 2)
            
        res["RECOMENDACIÓN"], res["Análisis"] = get_verdict(res["Chg 2v (%)"], res["Chg 4v (%)"], res["Chg 21v (%)"], tech)
        return res
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - CONFLUENCE & VOLUME TERMINAL")

with st.sidebar:
    st.header("⚙️ Configuración")
    min_vol = st.number_input("Volumen Mínimo (USDT)", value=1000000)
    tf = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
    
    if st.button("📡 1. CARGAR/ACTUALIZAR MERCADO"):
        st.session_state["all_symbols"] = fetch_universe(min_vol)
        st.session_state["ptr"] = 0
        st.success(f"Mercado cargado: {len(st.session_state['all_symbols'])} activos.")

    if st.session_state["all_symbols"]:
        total = len(st.session_state["all_symbols"])
        ptr = st.session_state["ptr"]
        batch_size = st.slider("Activos por lote", 10, 100, 30)
        
        if ptr < total:
            limit = min(ptr + batch_size, total)
            if st.button(f"🚀 ANALIZAR LOTE: {ptr} al {limit}", type="primary"):
                ex = get_exchange()
                targets = st.session_state["all_symbols"][ptr:limit]
                prog = st.progress(0)
                for i, sym in enumerate(targets):
                    res = analyze_asset(sym, tf, ex)
                    if res: st.session_state["persistent_list"].append(res)
                    prog.progress((i+1)/len(targets))
                st.session_state["ptr"] = limit
                st.rerun()

    if st.button("🗑️ LIMPIAR TODO"):
        st.session_state["persistent_list"] = []
        st.session_state["ptr"] = 0
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE RESULTADOS
# ─────────────────────────────────────────────
if st.session_state["persistent_list"]:
    df_accumulated = pd.DataFrame(st.session_state["persistent_list"]).drop_duplicates(subset="Activo", keep="last")
    
    st.subheader(f"📊 Inteligencia de Confluencia: {len(df_accumulated)} activos")
    
    def style_rows(val):
        try:
            v = str(val)
            if "VERDE" in v or "SUBIENDO" in v or "ALCISTA" in v or "COMPRA" in v: 
                return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if "ROJA" in v or "BAJANDO" in v or "BAJISTA" in v or "VENTA" in v: 
                return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
            if isinstance(val, (int, float)) and val > 100: return 'color: #1B5E20; font-weight: bold;'
        except: pass
        return ''

    # Ordenar por el mayor cambio de volumen inmediato
    df_accumulated = df_accumulated.sort_values(by="Chg 2v (%)", ascending=False)
    
    # Reordenar columnas para prioridad visual
    prio_cols = ["Activo", "RECOMENDACIÓN", "HA", "MACD Hist", "MACD Cross", "Precio"]
    other_cols = [c for c in df_accumulated.columns if c not in prio_cols and c != "Análisis"]
    df_accumulated = df_accumulated[prio_cols + other_cols + ["Análisis"]]

    st.dataframe(df_accumulated.style.map(style_rows), use_container_width=True, height=600)
    st.download_button("📥 Descargar Reporte", df_accumulated.to_csv(index=False), "sly_confluence.csv")
else:
    st.info("👈 Sincroniza y analiza un lote para obtener señales de confluencia.")
