import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACD MATRIX v28.5")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #00E676; padding-bottom: 10px; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    .sidebar .sidebar-content { background-color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #004D40; font-size: 20px; font-weight: bold; }
    .filter-section { background-color: #E8F5E9; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 10px; }
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
# NÚCLEO TÉCNICO
# ─────────────────────────────────────────────
def analyze_macd_logic(symbol, tf_code, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 35: return None
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        m_line_series = macd["MACD_12_26_9"]
        m_line = m_line_series.iloc[-1]
        m_sig = macd["MACDs_12_26_9"].iloc[-1]
        m_hist = macd["MACDh_12_26_9"].iloc[-1]
        m_hist_prev = macd["MACDh_12_26_9"].iloc[-2]

        m0_status = "SOBRE 0" if m_line > 0 else "BAJO 0"
        if tf_code == "1m":
            last_5 = m_line_series.tail(6).tolist()
            for i in range(1, len(last_5)):
                if last_5[i-1] <= 0 and last_5[i] > 0:
                    m0_status = "⚡ CROSS UP"
                    break
                elif last_5[i-1] >= 0 and last_5[i] < 0:
                    m0_status = "⚡ CROSS DOWN"
                    break

        return {
            "m0": m0_status,
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
            row = {"Activo": sym.split(":")[0].replace("/USDT", ""), "Precio": f"{ticker['last']:,.4f}"}
            for label, tf_code in TIMEFRAMES.items():
                data = analyze_macd_logic(sym, tf_code, ex)
                if data:
                    row[f"{label} MACD 0"], row[f"{label} Hist."], row[f"{label} Cruce"] = data["m0"], data["hist"], data["cross"]
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
        if "CROSS UP" in v: return 'background-color: #00E676; color: black; font-weight: 900;'
        if "CROSS DOWN" in v: return 'background-color: #D50000; color: white; font-weight: 900;'
        if any(x in v for x in ["SOBRE 0", "SUBIENDO", "ALCISTA"]): return 'background-color: #C8E6C9; color: #1B5E20;'
        if any(x in v for x in ["BAJO 0", "BAJANDO", "BAJISTA"]): return 'background-color: #FFCDD2; color: #B71C1C;'
        return ''
    try: return df.style.map(apply_color)
    except: return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL (BARRA LATERAL)
# ─────────────────────────────────────────────
st.title("🛡️ SLY - OMNI FILTER MATRIX v28.5")

with st.sidebar:
    st.header("⚙️ 1. Configuración de Escaneo")
    min_vol = st.number_input("Volumen Mínimo 24h (USDT):", value=1000000, step=100000)
    all_sym = get_filtered_symbols(min_vol)
    
    if all_sym:
        st.info(f"Activos líquidos: {len(all_sym)}")
        batch_size = st.number_input("Monedas por lote:", 5, 100, 20)
        num_lotes = len(all_sym) // batch_size + (1 if len(all_sym) % batch_size > 0 else 0)
        lote_options = [f"Lote {i+1} ({(i*batch_size)} a {min((i+1)*batch_size, len(all_sym))})" for i in range(num_lotes)]
        selected_lote_str = st.selectbox("Seleccionar Lote:", lote_options)
        selected_lote_idx = lote_options.index(selected_lote_str)
        targets_to_scan = all_sym[selected_lote_idx * batch_size : (selected_lote_idx + 1) * batch_size]
        
        acc = st.checkbox("Acumular resultados", value=True)
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["matrix_results"] = scan_batch(targets_to_scan, acc)
            st.rerun()

    if st.session_state["matrix_results"]:
        st.divider()
        st.header("🔍 2. Filtros de Resultados")
        df_full = pd.DataFrame(st.session_state["matrix_results"])
        
        # Filtro de nombre
        search = st.text_input("Buscar Activo (ej: BTC):").upper()
        
        # Filtro por Cruces de 1m (Gatillo rápido)
        m1_filter = st.multiselect("Filtrar 1m MACD 0:", df_full["1m MACD 0"].unique(), default=df_full["1m MACD 0"].unique())
        
        # Filtro por Tendencia 1D (Sesgo Macro)
        d1_filter = st.multiselect("Filtrar 1D Cruce:", df_full["1D Cruce"].unique(), default=df_full["1D Cruce"].unique())
        
        # Filtro por Impulso 1H (Momentum)
        h1_filter = st.multiselect("Filtrar 1H Hist.:", df_full["1H Hist."].unique(), default=df_full["1H Hist."].unique())

    if st.button("🗑️ Limpiar Todo", use_container_width=True):
        st.session_state["matrix_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO FINAL CON FILTROS APLICADOS
# ─────────────────────────────────────────────
if st.session_state["matrix_results"]:
    df = pd.DataFrame(st.session_state["matrix_results"])
    
    # Aplicación de Filtros
    if search:
        df = df[df["Activo"].str.contains(search)]
    df = df[df["1m MACD 0"].isin(m1_filter)]
    df = df[df["1D Cruce"].isin(d1_filter)]
    df = df[df["1H Hist."].isin(h1_filter)]
    
    # Ordenar columnas
    base_cols = ["Activo", "Precio"]
    tf_cols = []
    for tf in TIMEFRAMES.keys():
        tf_cols.extend([f"{tf} MACD 0", f"{tf} Hist.", f"{tf} Cruce"])
    
    df = df[base_cols + tf_cols]
    
    st.subheader(f"📊 Matriz Inteligente ({len(df)} activos filtrados)")
    st.dataframe(style_matrix(df), use_container_width=True, height=750)
else:
    st.info("👈 Configure el volumen y ejecute un lote para generar la matriz.")

with st.expander("📗 MANUAL DE FILTRADO"):
    st.markdown("""
    1.  **Escaneo:** Procesa lotes de activos. Los datos se guardan en memoria.
    2.  **Búsqueda:** Escribe el nombre de una moneda para aislarla.
    3.  **Filtros Rápidos:** 
        *   Usa el filtro de **1m MACD 0** para ver solo monedas con `⚡ CROSS UP`.
        *   Usa el filtro de **1D Cruce** para ver solo monedas en `ALCISTA` macro.
        *   Usa el filtro de **1H Hist.** para ver monedas con impulso `SUBIENDO`.
    """)
