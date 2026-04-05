import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACD MATRIX v27.5")

# CSS para máxima legibilidad institucional
st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #00E676; padding-bottom: 10px; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    .stNumberInput, .stRadio, .stCheckbox { background-color: white; padding: 10px; border-radius: 8px; border: 1px solid #DDD; }
    [data-testid="stMetricValue"] { color: #004D40; font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "matrix_results" not in st.session_state:
    st.session_state["matrix_results"] = []

TIMEFRAMES = {
    "1m": "1m", "30m": "30m", "1H": "1h", "4H": "4h", "12H": "12h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

def get_filtered_symbols(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        # Filtramos por par USDT y por volumen mínimo
        valid_symbols = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s:
                vol = t.get('quoteVolume', 0)
                if vol >= min_vol:
                    valid_symbols.append(s)
        return sorted(valid_symbols)
    except: return []

# ─────────────────────────────────────────────
# NÚCLEO TÉCNICO MACD
# ─────────────────────────────────────────────
def analyze_macd_logic(symbol, tf_code, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 35: return None
        
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
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
        prog.progress((idx+1)/len(targets), text=f"Procesando {sym.split(':')[0]}...")
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
                    for c in ["MACD 0", "Hist.", "Cruce"]: row[f"{label} {c}"] = "-"
            
            new_results.append(row)
            time.sleep(0.05)
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
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if any(x in v for x in ["BAJO 0", "BAJANDO", "BAJISTA"]): 
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        return ''
    
    try:
        return df.style.map(apply_color)
    except:
        return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY - MACD IMPULSE MATRIX v27.5")

with st.sidebar:
    st.header("⚙️ Configuración")
    
    min_vol = st.number_input("Volumen Mínimo 24h (USDT):", value=1000000, step=100000)
    
    analysis_mode = st.radio("Filtro de Activos:", ["Mercado x Volumen", "Watchlist"])
    
    if analysis_mode == "Mercado x Volumen":
        all_sym = get_filtered_symbols(min_vol)
        st.success(f"Activos con Vol > {min_vol:,}: {len(all_sym)}")
        b_size = st.number_input("Lote a escanear:", 5, 50, 20)
        pointer = st.number_input("Desde el índice:", 0, max(0, len(all_sym)-1), 0)
        targets_to_scan = all_sym[pointer:pointer+b_size]
    else:
        full_list = get_filtered_symbols(0)
        targets_to_scan = st.multiselect("Activos específicos:", full_list)

    acc = st.checkbox("Acumular resultados", value=True)
    
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        if targets_to_scan:
            st.session_state["matrix_results"] = scan_batch(targets_to_scan, acc)
            st.rerun()
        else:
            st.warning("No hay activos que cumplan el criterio.")

    if st.button("🗑️ Limpiar Pantalla"):
        st.session_state["matrix_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO FINAL
# ─────────────────────────────────────────────
if st.session_state["matrix_results"]:
    df = pd.DataFrame(st.session_state["matrix_results"])
    
    # Reordenamiento lógico
    base_cols = ["Activo", "Precio"]
    tf_cols = []
    for tf in TIMEFRAMES.keys():
        tf_cols.extend([f"{tf} MACD 0", f"{tf} Hist.", f"{tf} Cruce"])
    
    df = df[base_cols + tf_cols]
    
    st.dataframe(style_matrix(df), use_container_width=True, height=700)
else:
    st.info("👈 Ajuste el volumen mínimo y el lote, luego presione Iniciar Escaneo.")

with st.expander("📘 NOTAS TÉCNICAS"):
    st.markdown(f"""
    *   **Volumen Mínimo:** Solo se analizan activos que mueven más de {min_vol:,} USDT en las últimas 24h.
    *   **MACD Matrix:** Detecta la convergencia de impulso entre 1m y 1D.
    *   **Colores:** Verde (Aceleración/Tendencia +), Rojo (Desaceleración/Tendencia -).
    """)
