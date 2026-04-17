import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | VOLUME & ALPHA PERSISTENCE")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #00E676; padding-bottom: 10px; }
    .stDataFrame { background-color: white; border-radius: 10px; border: 1px solid #DDD; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #EEE; text-align: center; }
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
# LÓGICA DE RECOMENDACIÓN (ALPHA + VOLUMEN)
# ─────────────────────────────────────────────
def get_verdict(v2, v21, delta):
    # Lógica de Alpha Rating
    if delta > 4: alpha_label = "ALPHA STRIKE"
    elif delta > 0: alpha_label = "OUTPERFORMER"
    else: alpha_label = "LAGGARD"

    # Lógica de Recomendación de Volumen
    if v2 > 150: rec = "🔥 PUMP INMINENTE"
    elif v21 > 60: rec = "🐳 ACUMULACIÓN"
    elif v2 < -50: rec = "❄️ SECADO"
    else: rec = "⚖️ NEUTRAL"

    return rec, alpha_label

def analyze_volume_and_alpha(symbol, tf, exchange, btc_perf):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        
        # Rendimiento de la moneda
        price_now = df['c'].iloc[-1]
        price_prev = df['c'].iloc[-2]
        asset_perf = ((price_now / price_prev) - 1) * 100
        delta_btc = asset_perf - btc_perf
        
        res = {
            "Activo": symbol.replace("/USDT", ""),
            "Precio": price_now,
            "Vs BTC (Delta)": round(delta_btc, 2)
        }
        
        # Cálculos de volumen acumulado
        for p in [2, 4, 21, 42]:
            curr = df['v'].tail(p).sum()
            prev = df['v'].iloc[-(p*2):-p].sum()
            chg = ((curr - prev) / prev * 100) if prev > 0 else 0
            res[f"Vol {p}v"] = f"{curr:,.0f}"
            res[f"Chg {p}v (%)"] = round(chg, 2)
            
        res["RECOMENDACIÓN"], res["Alpha Rating"] = get_verdict(res["Chg 2v (%)"], res["Chg 21v (%)"], delta_btc)
        return res
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - PERSISTENT VOLUME & ALPHA ENGINE")

with st.sidebar:
    st.header("⚙️ Configuración")
    min_vol = st.number_input("Volumen Mínimo (USDT)", value=1000000)
    tf = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
    
    if st.button("📡 1. CARGAR/ACTUALIZAR MERCADO"):
        st.session_state["all_symbols"] = fetch_universe(min_vol)
        st.session_state["ptr"] = 0
        st.session_state["persistent_list"] = []
        st.success(f"Mercado cargado: {len(st.session_state['all_symbols'])} activos.")

    if st.session_state["all_symbols"]:
        total = len(st.session_state["all_symbols"])
        current_ptr = st.session_state["ptr"]
        batch_size = st.slider("Activos por lote", 10, 100, 30)
        
        if current_ptr < total:
            limit = min(current_ptr + batch_size, total)
            if st.button(f"🚀 ANALIZAR LOTE: {current_ptr} al {limit}", type="primary"):
                ex = get_exchange()
                
                # Obtener rendimiento de BTC para el Delta
                btc_ticker = ex.fetch_ticker('BTC/USDT')
                btc_perf = btc_ticker.get('percentage', 0)
                
                targets = st.session_state["all_symbols"][current_ptr:limit]
                prog = st.progress(0)
                for i, sym in enumerate(targets):
                    res = analyze_volume_and_alpha(sym, tf, ex, btc_perf)
                    if res:
                        st.session_state["persistent_list"].append(res)
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
    
    # Orden lógico de columnas
    prio = ["Activo", "RECOMENDACIÓN", "Alpha Rating", "Vs BTC (Delta)", "Precio", "Chg 2v (%)", "Chg 21v (%)"]
    rest = [c for c in df_accumulated.columns if c not in prio]
    df_accumulated = df_accumulated[prio + rest]

    st.subheader(f"📊 Inteligencia Acumulada: {len(df_accumulated)} activos")
    
    def style_logic(val):
        try:
            if "PUMP" in str(val) or "STRIKE" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if "ACUMULACIÓN" in str(val) or "OUTPERFORMER" in str(val): return 'background-color: #E3F2FD; color: #0D47A1; font-weight: bold;'
            if isinstance(val, (int, float)) and val > 0: return 'color: #1B5E20; font-weight: bold;'
            if isinstance(val, (int, float)) and val < 0: return 'color: #B71C1C;'
        except: pass
        return ''

    df_final = df_accumulated.sort_values(by="Vs BTC (Delta)", ascending=False)
    
    # Manejo robusto de .map para Pandas 2.1+
    try:
        styled_df = df_final.style.map(style_logic)
    except AttributeError:
        styled_df = df_final.style.applymap(style_logic)

    st.dataframe(styled_df, use_container_width=True, height=600)
    st.download_button("📥 Bajar Reporte CSV", df_final.to_csv(index=False), "sly_alpha_volume.csv")
else:
    st.info("👈 Presiona 'Sincronizar' y luego 'Analizar Lote' para empezar.")
