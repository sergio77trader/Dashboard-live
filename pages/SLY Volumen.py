import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | VOLUME PERSISTENCE ENGINE")

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
    st.session_state["persistent_list"] = [] # Usamos lista para evitar errores de concatenación
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
# LÓGICA DE RECOMENDACIÓN
# ─────────────────────────────────────────────
def get_verdict(v2, v4, v21, v42):
    if v2 > 150 and v4 > 100: return "🔥 PUMP INMINENTE", "Inyección explosiva."
    if v21 > 60 and v42 > 40: return "🐳 ACUMULACIÓN", "Manos grandes comprando."
    if v2 < -50: return "❄️ SECADO", "Sin interés."
    return "⚖️ NEUTRAL", "Flujo normal."

def analyze_volume(symbol, tf, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        res = {"Activo": symbol.replace("/USDT", ""), "Precio": df['c'].iloc[-1]}
        
        for p in [2, 4, 21, 42]:
            curr = df['v'].tail(p).sum()
            prev = df['v'].iloc[-(p*2):-p].sum()
            chg = ((curr - prev) / prev * 100) if prev > 0 else 0
            res[f"Vol {p}v"] = f"{curr:,.0f}"
            res[f"Chg {p}v (%)"] = round(chg, 2)
            
        res["RECOMENDACIÓN"], res["Análisis"] = get_verdict(res["Chg 2v (%)"], res["Chg 4v (%)"], res["Chg 21v (%)"], res["Chg 42v (%)"])
        return res
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - PERSISTENT VOLUME TERMINAL")

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
        current_ptr = st.session_state["ptr"]
        batch_size = st.slider("Activos por lote", 10, 100, 30)
        
        if current_ptr < total:
            limit = min(current_ptr + batch_size, total)
            if st.button(f"🚀 ANALIZAR LOTE: {current_ptr} al {limit}", type="primary"):
                ex = get_exchange()
                targets = st.session_state["all_symbols"][current_ptr:limit]
                
                prog = st.progress(0)
                for i, sym in enumerate(targets):
                    res = analyze_volume(sym, tf, ex)
                    if res:
                        # AGREGAR A LA LISTA PERSISTENTE
                        st.session_state["persistent_list"].append(res)
                    prog.progress((i+1)/len(targets))
                
                st.session_state["ptr"] = limit
                st.rerun() # Forzar refresco para mostrar datos acumulados

    if st.button("🗑️ LIMPIAR TODO"):
        st.session_state["persistent_list"] = []
        st.session_state["ptr"] = 0
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE RESULTADOS
# ─────────────────────────────────────────────
if st.session_state["persistent_list"]:
    # Convertir lista a DataFrame
    df_accumulated = pd.DataFrame(st.session_state["persistent_list"]).drop_duplicates(subset="Activo", keep="last")
    
    st.subheader(f"📊 Inteligencia Acumulada: {len(df_accumulated)} activos")
    
    # Estilo institucional
    def style_rows(val):
        try:
            if "PUMP" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if "ACUMULACIÓN" in str(val): return 'background-color: #E3F2FD; color: #0D47A1; font-weight: bold;'
            if isinstance(val, (int, float)) and val > 100: return 'color: #1B5E20; font-weight: bold;'
            if isinstance(val, (int, float)) and val < -40: return 'color: #B71C1C;'
        except: pass
        return ''

    # Ordenar por el mayor cambio de volumen en las últimas 2 velas
    df_accumulated = df_accumulated.sort_values(by="Chg 2v (%)", ascending=False)
    
    st.dataframe(df_accumulated.style.map(style_rows), use_container_width=True, height=600)
    
    st.download_button("📥 Bajar Reporte", df_accumulated.to_csv(index=False), "sly_volume.csv")
else:
    st.info("👈 Presiona 'Sincronizar' y luego 'Analizar Lote' para ir acumulando monedas.")
