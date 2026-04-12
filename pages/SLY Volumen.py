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
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #EEE; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA ---
if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []
if "pointer" not in st.session_state:
    st.session_state["pointer"] = 0

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
        valid = []
        for s, t in tickers.items():
            if "/USDT" in s:
                v = t.get('quoteVolume') or t.get('baseVolume') or 0
                if v >= min_vol:
                    valid.append(s)
        return sorted(valid)
    except: return []

# ─────────────────────────────────────────────
# LÓGICA DE RECOMENDACIÓN (SCORING)
# ─────────────────────────────────────────────
def get_vol_recommendation(data):
    # Extraer deltas
    v2 = data['Chg 2v (%)']
    v4 = data['Chg 4v (%)']
    v21 = data['Chg 21v (%)']
    v42 = data['Chg 42v (%)']

    if v2 > 150 and v4 > 100:
        return "🔥 PUMP INMINENTE", "Inyección explosiva de capital en el micro-plazo."
    if v21 > 60 and v42 > 40:
        return "🐳 ACUMULACIÓN BALLENA", "Movimiento sostenido de manos grandes."
    if v2 > 80 and v21 < 0:
        return "⚡ SCALPING OPPORTUNITY", "Spike de volumen puntual para trades rápidos."
    if v2 < -50:
        return "❄️ SECADO (EVITAR)", "Falta total de interés comprador."
    
    return "⚖️ NEUTRAL", "Flujo de órdenes normal."

# ─────────────────────────────────────────────
# ESCÁNER TÉCNICO
# ─────────────────────────────────────────────
def analyze_volume_logic(symbol, tf, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        periods = [2, 3, 4, 6, 21, 42]
        res = {"Activo": symbol.replace("/USDT", ""), "Precio": df['c'].iloc[-1]}

        for p in periods:
            curr_v = df['v'].tail(p).sum()
            prev_v = df['v'].iloc[-(p*2):-p].sum()
            change = ((curr_v - prev_v) / prev_v * 100) if prev_v > 0 else 0
            res[f"Vol {p}v"] = f"{curr_v:,.0f}"
            res[f"Chg {p}v (%)"] = round(change, 2)
        
        rec, logic = get_vol_recommendation(res)
        res["RECOMENDACIÓN"] = rec
        res["Análisis"] = logic
        return res
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - PERSISTENT VOLUME TERMINAL")

with st.sidebar:
    st.header("⚙️ Configuración")
    min_vol = st.number_input("Volumen Mínimo 24h (USDT)", value=1000000)
    tf = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
    
    if st.button("📡 1. SINCRONIZAR MERCADO"):
        st.session_state["all_symbols"] = fetch_universe(min_vol)
        st.session_state["pointer"] = 0
        st.rerun()

    if st.session_state["all_symbols"]:
        total = len(st.session_state["all_symbols"])
        ptr = st.session_state["pointer"]
        batch_size = st.slider("Activos por lote", 10, 50, 20)
        
        if ptr < total:
            next_limit = min(ptr + batch_size, total)
            if st.button(f"🚀 ANALIZAR LOTE {ptr} a {next_limit}", type="primary"):
                ex = get_exchange()
                targets = st.session_state["all_symbols"][ptr:next_limit]
                
                new_data = []
                prog = st.progress(0)
                for i, sym in enumerate(targets):
                    res = analyze_volume_logic(sym, tf, ex)
                    if res: new_data.append(res)
                    prog.progress((i+1)/len(targets))
                
                # Acumular
                if new_data:
                    df_new = pd.DataFrame(new_data)
                    st.session_state["accumulated_data"] = pd.concat([st.session_state["accumulated_data"], df_new]).drop_duplicates(subset="Activo")
                    st.session_state["pointer"] = next_limit
                st.rerun()

    if st.button("🗑️ RESETEAR RADAR"):
        st.session_state["accumulated_data"] = pd.DataFrame()
        st.session_state["pointer"] = 0
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE RESULTADOS
# ─────────────────────────────────────────────
if not st.session_state["accumulated_data"].empty:
    st.subheader(f"📊 Inteligencia de Volumen Acumulada ({len(st.session_state['accumulated_data'])} activos)")
    
    df_disp = st.session_state["accumulated_data"].copy()
    
    def style_table(val):
        try:
            v = str(val)
            if "PUMP" in v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if "ACUMULACIÓN" in v: return 'background-color: #E3F2FD; color: #0D47A1; font-weight: bold;'
            if "EVITAR" in v: return 'background-color: #FFCDD2; color: #B71C1C;'
            if "%" in v or isinstance(val, (int, float)):
                num = float(str(val).replace("%",""))
                if num > 100: return 'color: #1B5E20; font-weight: bold;'
                if num < -40: return 'color: #B71C1C;'
        except: pass
        return ''

    # Ordenar por mayor explosión en 2 velas
    df_disp = df_disp.sort_values(by="Chg 2v (%)", ascending=False)
    
    st.dataframe(df_disp.style.map(style_table), use_container_width=True, height=600)
    
    csv = df_disp.to_csv(index=False)
    st.download_button("📥 Descargar Reporte CSV", csv, "sly_volume_report.csv")
else:
    st.info("👈 Sincroniza el mercado y presiona 'Analizar Lote' para empezar a acumular datos.")

with st.expander("📘 GUÍA DE RECOMENDACIONES"):
    st.markdown("""
    *   **PUMP INMINENTE:** El volumen en las últimas 2 velas ha crecido más de un 150%. Entrada masiva de órdenes.
    *   **ACUMULACIÓN BALLENA:** El volumen de las últimas 42 velas es significativamente mayor al periodo anterior. Alguien grande está comprando sin hacer ruido.
    *   **SCALPING:** Spike de corto plazo pero sin soporte macro. Ideal para entrar y salir en minutos.
    """)
