import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | VOLUME CLIMAX v30.1")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stDataFrame { border: 1px solid #333; background-color: #161B22; }
    .status-panel { padding: 15px; border-radius: 10px; background-color: #1E1E1E; border: 1px solid #333; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

if "matrix_data" not in st.session_state:
    st.session_state["matrix_data"] = []

# ─────────────────────────────────────────────
# MOTOR DE DATOS RESILIENTE
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    # Probamos con Kucoin estándar (más estable para tickers)
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 40000})

def fetch_tickers_robust(min_vol):
    try:
        ex = get_exchange()
        st.write("📡 Conectando con el servidor de datos...")
        tickers = ex.fetch_tickers()
        
        valid = []
        for s, t in tickers.items():
            # Filtro más permisivo: que sea par USDT y que tenga volumen
            if "/USDT" in s:
                v_24h = t.get('quoteVolume') or t.get('baseVolume') or 0
                if v_24h >= min_vol:
                    valid.append({"symbol": s, "vol_24h": v_24h})
        
        df = pd.DataFrame(valid)
        if not df.empty:
            df = df.sort_values("vol_24h", ascending=False)
            return df["symbol"].tolist()
        return []
    except Exception as e:
        st.error(f"⚠️ Error de conexión API: {str(e)}")
        return []

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_cumulative_vol(symbol, tf, exchange):
    try:
        # Descarga de 100 velas para tener margen de comparación
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        if len(ohlcv) < 85: return None
        
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        periods = [2, 3, 4, 6, 21, 42]
        results = {"Activo": symbol.replace("/USDT", ""), "Precio": df['c'].iloc[-1]}

        for p in periods:
            # Bloque actual
            curr_vol = df['v'].tail(p).sum()
            # Bloque anterior para comparar %
            prev_vol = df['v'].iloc[-(p*2):-p].sum()
            
            change = ((curr_vol - prev_vol) / prev_vol * 100) if prev_vol > 0 else 0
            results[f"Vol {p}v"] = f"{curr_vol:,.0f}"
            results[f"Chg {p}v (%)"] = round(change, 2)

        return results
    except:
        return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - VOLUME CLIMAX MATRIX")

with st.sidebar:
    st.header("⚙️ Parámetros")
    min_vol_input = st.number_input("Volumen Mínimo 24h (USDT)", value=1000000, min_value=1)
    tf_input = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
    limit_input = st.slider("Cantidad de activos", 5, 50, 20)
    
    execute = st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True)

# ─────────────────────────────────────────────
# LÓGICA DE EJECUCIÓN
# ─────────────────────────────────────────────
if execute:
    symbols = fetch_tickers_robust(min_vol_input)
    
    if symbols:
        st.toast(f"✅ Universo cargado: {len(symbols)} monedas encontradas.")
        targets = symbols[:limit_input]
        
        ex = get_exchange()
        new_results = []
        
        prog = st.progress(0)
        status_text = st.empty()
        
        for i, sym in enumerate(targets):
            status_text.text(f"Analizando flujo: {sym}")
            res = calculate_cumulative_vol(sym, tf_input, ex)
            if res:
                new_results.append(res)
            prog.progress((i+1)/len(targets))
            time.sleep(0.1) # Evitar saturación
        
        st.session_state["matrix_data"] = new_results
        status_text.success(f"Análisis completado para {len(new_results)} activos.")
        st.rerun()
    else:
        st.error("No se encontraron activos. Verifica la conexión o baja el filtro de volumen.")

# ─────────────────────────────────────────────
# RENDERIZADO DE RESULTADOS
# ─────────────────────────────────────────────
if st.session_state["matrix_data"]:
    df_final = pd.DataFrame(st.session_state["matrix_data"])
    
    def style_vol(val):
        try:
            v = float(val)
            if v > 150: return 'background-color: #1B5E20; color: white; font-weight: bold;'
            if v > 80: return 'background-color: #2E7D32; color: white;'
            if v < -40: return 'color: #FF5252;'
        except: pass
        return ''

    chg_cols = [c for c in df_final.columns if "(%)" in c]
    
    st.subheader(f"📊 Anomalías de Volumen en {tf_input.upper()}")
    st.dataframe(
        df_final.style.map(style_vol, subset=chg_cols),
        use_container_width=True,
        height=600
    )
    
    if st.button("🗑️ Limpiar Pantalla"):
        st.session_state["matrix_data"] = []
        st.rerun()
else:
    st.info("👈 Ajuste parámetros y presione el botón rojo para iniciar el motor.")
