import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACD MATRIX v27.6")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #00E676; padding-bottom: 10px; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    .sidebar .sidebar-content { background-image: linear-gradient(#FFFFFF, #F8F9FA); }
    [data-testid="stMetricValue"] { color: #004D40; font-size: 20px; font-weight: bold; }
    .stSelectbox, .stNumberInput { background-color: white; }
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
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym.split(':')[0]}...")
        try:
            ticker = ex.fetch_ticker(sym)
            row = {
                "Activo": sym.split(":")[0].replace("/USDT", ""),
                "Precio": f"{ticker['last']:,.4f}"
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
st.title("🛡️ SLY - MACD MATRIX v27.6")

with st.sidebar:
    st.header("⚙️ Configuración")
    
    min_vol = st.number_input("Volumen Mínimo 24h (USDT):", value=1000000, step=100000)
    all_sym = get_filtered_symbols(min_vol)
    
    if all_sym:
        st.success(f"Activos Líquidos: {len(all_sym)}")
        
        batch_size = st.number_input("Monedas por lote:", 5, 100, 20)
        
        # Cálculo de Lotes
        num_lotes = len(all_sym) // batch_size + (1 if len(all_sym) % batch_size > 0 else 0)
        
        lote_options = []
        for i in range(num_lotes):
            start_num = i * batch_size
            end_num = min((i + 1) * batch_size, len(all_sym))
            lote_options.append(f"Lote {i+1} ({start_num} a {end_num})")
        
        selected_lote_str = st.selectbox("Seleccionar Lote:", lote_options)
        selected_lote_idx = lote_options.index(selected_lote_str)
        
        targets_to_scan = all_sym[selected_lote_idx * batch_size : (selected_lote_idx + 1) * batch_size]
        
        acc = st.checkbox("Acumular resultados", value=True)
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["matrix_results"] = scan_batch(targets_to_scan, acc)
            st.rerun()
    else:
        st.warning("No hay activos con ese volumen.")

    if st.button("🗑️ Limpiar Pantalla", use_container_width=True):
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
    st.info("👈 Seleccione un lote y presione Iniciar para procesar la data.")

with st.expander("📘 MANUAL OPERATIVO"):
    st.markdown(f"""
    1.  **Lotes:** El universo se divide automáticamente. Procesa el Lote 1, luego el 2, etc.
    2.  **Acumular:** Si está marcado, los resultados del Lote 2 se sumarán a los del Lote 1.
    3.  **Confluencia:** Busca activos donde múltiples temporalidades estén en **verde**.
    """)
