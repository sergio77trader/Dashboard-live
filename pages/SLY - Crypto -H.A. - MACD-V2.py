import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | MACD MATRIX")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 11px; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

if "matrix_results" not in st.session_state:
    st.session_state["matrix_results"] = []

# Temporalidades solicitadas
TIMEFRAMES = {
    "1m": "1m",
    "30m": "30m",
    "1H": "1h",
    "4H": "4h",
    "12H": "12h",
    "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    # Usamos KuCoin Futures por compatibilidad y menor restricción de IP
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_all_symbols():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s in tickers if "/USDT:USDT" in s]
    except: return []

# ─────────────────────────────────────────────
# NÚCLEO TÉCNICO
# ─────────────────────────────────────────────
def analyze_macd_logic(symbol, tf_code, exchange):
    try:
        # Descarga optimizada: 100 velas son suficientes para MACD (12,26,9)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 35: return None
        
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        
        # Cálculo MACD (12, 26, 9)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        m_line = macd["MACD_12_26_9"].iloc[-1]
        m_sig = macd["MACDs_12_26_9"].iloc[-1]
        m_hist = macd["MACDh_12_26_9"].iloc[-1]
        m_hist_prev = macd["MACDh_12_26_9"].iloc[-2]

        return {
            "m0": "SOBRE 0" if m_line > 0 else "BAJO 0",
            "hist": "SUBIENDO" if m_hist > m_hist_prev else "BAJANDO",
            "cross": "ALCISTA" if m_line > m_sig else "BAJISTA"
        }
    except: return None

def scan_batch(targets, acc):
    ex = get_exchange()
    new_results = []
    prog = st.progress(0)
    
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym.split(':')[0]}...")
        try:
            ticker = ex.fetch_ticker(sym)
            price = ticker["last"]
            row = {
                "Activo": sym.split(":")[0].replace("/USDT", ""),
                "Precio": f"{price:,.4f}"
            }
            
            for label, tf_code in TIMEFRAMES.items():
                data = analyze_macd_logic(sym, tf_code, ex)
                if data:
                    row[f"{label} MACD 0"] = data["m0"]
                    row[f"{label} Hist."] = data["hist"]
                    row[f"{label} Cruce"] = data["cross"]
                else:
                    row[f"{label} MACD 0"] = "-"
                    row[f"{label} Hist."] = "-"
                    row[f"{label} Cruce"] = "-"
            
            new_results.append(row)
            time.sleep(0.05) # Jitter de seguridad
        except: continue
        
    prog.empty()
    if acc:
        curr = {x["Activo"]: x for x in st.session_state["matrix_results"]}
        for r in new_results: curr[r["Activo"]] = r
        return list(curr.values())
    return new_results

def style_matrix(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["SOBRE 0", "SUBIENDO", "ALCISTA"]): 
            return 'color: #00E676; font-weight: bold;'
        if any(x in v for x in ["BAJO 0", "BAJANDO", "BAJISTA"]): 
            return 'color: #FF5252;'
        return ''
    
    try:
        return df.style.map(apply_color)
    except:
        return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - MACD IMPULSE MATRIX")

with st.sidebar:
    st.header("🎯 Configuración")
    
    analysis_mode = st.radio("Modo:", ["Mercado (Lotes)", "Watchlist"])
    
    if analysis_mode == "Mercado (Lotes)":
        all_sym = get_all_symbols()
        st.write(f"Total: {len(all_sym)} activos")
        b_size = st.number_input("Lote:", 10, 50, 20)
        pointer = st.number_input("Desde índice:", 0, len(all_sym), 0)
        targets_to_scan = all_sym[pointer:pointer+b_size]
    else:
        full_list = get_all_symbols()
        targets_to_scan = st.multiselect("Activos:", full_list)

    acc = st.checkbox("Acumular resultados", value=True)
    
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        if targets_to_scan:
            st.session_state["matrix_results"] = scan_batch(targets_to_scan, acc)
            st.rerun()

    if st.button("Limpiar Pantalla"):
        st.session_state["matrix_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO FINAL
# ─────────────────────────────────────────────
if st.session_state["matrix_results"]:
    df = pd.DataFrame(st.session_state["matrix_results"])
    
    # Reordenamiento lógico de columnas
    base_cols = ["Activo", "Precio"]
    tf_cols = []
    for tf in TIMEFRAMES.keys():
        tf_cols.extend([f"{tf} MACD 0", f"{tf} Hist.", f"{tf} Cruce"])
    
    df = df[base_cols + tf_cols]
    
    st.dataframe(style_matrix(df), use_container_width=True, height=800)
else:
    st.info("👈 Configure los activos y presione Iniciar para generar la matriz de impulso.")

with st.expander("📘 NOTAS TÉCNICAS"):
    st.markdown("""
    *   **MACD 0:** Define si la tendencia es de valor positivo o negativo.
    *   **Histograma:** Indica si el momentum actual se está acelerando o frenando.
    *   **Cruce:** Confirmación de entrada/salida (MACD vs Signal).
    *   *Datos procesados directamente desde KuCoin Futures.*
    """)
