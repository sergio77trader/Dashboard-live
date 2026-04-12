import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | VOLUME CLIMAX TERMINAL")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stDataFrame { border: 1px solid #333; }
    .alert-box { padding: 10px; border-radius: 5px; background-color: #1B5E20; color: white; font-weight: bold; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE DATOS (REDUNDANCIA BINANCE/KUCOIN)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    # Usamos KuCoin por defecto para evitar bloqueos de IP en Streamlit Cloud
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

def fetch_tickers(min_volume_filter):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        # Filtramos solo activos líquidos y pares USDT
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_volume_filter:
                valid.append({"symbol": s, "vol_24h": t["quoteVolume"]})
        df = pd.DataFrame(valid).sort_values("vol_24h", ascending=False)
        return df["symbol"].tolist()
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS DE VOLUMEN (LÓGICA SLY ORIGINAL)
# ─────────────────────────────────────────────
def calculate_cumulative_vol(symbol, tf, exchange):
    try:
        # Pedimos 100 velas para cubrir el periodo de 42 y sus comparativas
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        
        periods = [2, 3, 4, 6, 21, 42]
        results = {"Activo": symbol.split(":")[0].replace("/USDT", ""), "Precio": df['c'].iloc[-1]}
        alerts = []

        for p in periods:
            # Volumen Acumulado Actual
            curr_vol = df['v'].tail(p).sum()
            # Volumen Acumulado Anterior (el bloque de P velas antes de las actuales)
            prev_vol = df['v'].iloc[-(p*2):-p].sum()
            
            # % Cambio (Delta de Volumen)
            change = ((curr_vol - prev_vol) / prev_vol * 100) if prev_vol > 0 else 0
            
            results[f"Vol {p}v"] = f"{curr_vol:,.0f}"
            results[f"Chg {p}v (%)"] = round(change, 2)
            
            # Umbral de Alerta Institucional: > 100% de aumento de volumen
            if change > 100:
                alerts.append(f"{p}v")

        return results, alerts
    except: return None, []

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - VOLUME CLIMAX MATRIX")
st.sidebar.header("🎯 Parámetros de Escaneo")

min_vol = st.sidebar.number_input("Volumen 24h Mínimo (USDT)", value=5000000, step=1000000)
tf = st.sidebar.selectbox("Temporalidad", ["1m", "5m", "15m", "1H", "4H", "1D"], index=2)
batch_size = st.sidebar.slider("Activos por escaneo", 5, 50, 20)

if "matrix_data" not in st.session_state:
    st.session_state["matrix_data"] = []

if st.sidebar.button("🚀 INICIAR ESCANEO DE VOLUMEN"):
    symbols = fetch_tickers(min_vol)
    targets = symbols[:batch_size]
    
    ex = get_exchange()
    new_results = []
    
    prog = st.progress(0)
    for i, sym in enumerate(targets):
        prog.progress((i+1)/len(targets), text=f"Analizando flujo de órdenes: {sym}")
        res, alerts = calculate_cumulative_vol(sym, tf, ex)
        if res:
            if alerts:
                st.toast(f"🚨 Anomalía detectada en {res['Activo']} ({', '.join(alerts)})")
            new_results.append(res)
        time.sleep(0.1) # Jitter de seguridad

    st.session_state["matrix_data"] = new_results
    st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE LA MATRIZ
# ─────────────────────────────────────────────
if st.session_state["matrix_data"]:
    df_final = pd.DataFrame(st.session_state["matrix_data"])
    
    # Estilo de la tabla
    def color_vol(val):
        try:
            v = float(val)
            if v > 200: return 'background-color: #1B5E20; color: #white;' # Explosión masiva
            if v > 100: return 'background-color: #2E7D32; color: white;'  # Inyección institucional
            if v < -50: return 'color: #FF5252;' # Secado de volumen
        except: pass
        return ''

    # Mostrar alertas críticas primero
    st.subheader(f"📊 Matriz de Volumen Acumulado - {tf}")
    
    # Columnas de porcentaje para aplicar color
    chg_cols = [c for c in df_final.columns if "(%)" in c]
    
    st.dataframe(
        df_final.style.map(color_vol, subset=chg_cols),
        use_container_width=True,
        height=600
    )
    
    if st.button("🗑️ Limpiar Resultados"):
        st.session_state["matrix_data"] = []
        st.rerun()
else:
    st.info("👈 Ajuste el filtro de volumen y presione 'Iniciar Escaneo'. El sistema buscará anomalías en los periodos de 2 a 42 velas.")

# ─────────────────────────────────────────────
# MANUAL PARA EL OPERADOR
# ─────────────────────────────────────────────
with st.expander("📘 LÓGICA DE DETECCIÓN (SystemaTrader)"):
    st.markdown("""
    ### ¿Cómo interpretar el Delta de Volumen?
    1.  **Chg 2v/3v/4v > 100%:** Entrada inminente de dinero. Si el precio acompaña, es el inicio de un 'Pump' o ruptura institucional.
    2.  **Chg 21v/42v > 50%:** Acumulación macro. Las ballenas están posicionándose en este activo de forma sostenida.
    3.  **Color Verde Oscuro:** El volumen actual duplica al volumen anterior. Es una **Anomalía Crítica**.
    """)
