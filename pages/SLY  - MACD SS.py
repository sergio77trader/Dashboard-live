import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACD PRE-CROSS SNIPER")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1C1E21; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 3px solid #2962FF; padding-bottom: 10px; }
    .stDataFrame { background-color: white; border-radius: 10px; border: 1px solid #DDD; }
    [data-testid="stMetricValue"] { color: #004D40; font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Lista Maestra para asegurar disponibilidad en Binance
BINANCE_WHITELIST = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'LINK', 'MATIC', 'SHIB', 'TRX', 'LTC', 'BCH', 'UNI', 'NEAR', 'SUI', 'APT', 'OP', 'ARB', 'TIA', 'INJ', 'FET', 'RNDR', 'STX', 'KAS', 'ORDI', 'FIL', 'ATOM', 'IMX', 'HBAR', 'LDO', 'ICP', 'GRT', 'AAVE', 'MKR', 'RUNE', 'EGLD', 'SEI', 'PEPE', 'WIF', 'FLOKI', 'BONK', 'JUP', 'PYTH', 'ENA', 'BOME', 'STRK', 'DYDX', 'GALA', 'ALGO', 'FLOW', 'VET', 'AXS', 'SAND', 'MANA', 'THETA', 'CHZ', 'BEAM', 'PENDLE', 'ALT', 'MANTA', 'PIXEL', 'DYM', 'RON', 'ARKM', 'ID', 'MAV', 'WOO', 'JTO', 'ORDI', 'SATS', 'RATS', 'MYRO', 'METIS', 'GNO', 'ENS', 'ASTR', 'WLD', 'ZETA', 'XAI', 'TAO', 'TON', 'NOT', 'TURBO', 'MEME', 'LISTA', 'IO', 'ZK', 'ZRO', 'BANANA', 'RENDER', 'FIDA', 'EIGEN', 'SCR', 'COW', 'CETUS', 'PNUT', 'ACT', 'NEIRO', 'MOODENG', 'THE', 'VANA', 'PENGU']

if "accumulated_results" not in st.session_state:
    st.session_state["accumulated_results"] = []
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []
if "pointer" not in st.session_state:
    st.session_state["pointer"] = 0

# ─────────────────────────────────────────────
# MOTOR DE DATOS (KUCOIN AS PROXY FOR BINANCE)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

def fetch_filtered_universe(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            base = s.split('/')[0]
            if "/USDT:USDT" in s and (base in BINANCE_WHITELIST or t.get("quoteVolume", 0) >= min_vol):
                valid.append(s)
        return sorted(list(set(valid)))
    except: return []

# ─────────────────────────────────────────────
# LÓGICA DE PRE-CRUCE MACD
# ─────────────────────────────────────────────
def analyze_macd_pre_cross(symbol, exchange):
    try:
        # Analizamos 4 Horas como timeframe principal
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        
        hist = macd["MACDh_12_26_9"]
        macd_line = macd["MACD_12_26_9"]
        signal_line = macd["MACDs_12_26_9"]
        
        curr_h = hist.iloc[-1]
        prev_h = hist.iloc[-2]
        curr_m = macd_line.iloc[-1]
        curr_s = signal_line.iloc[-1]
        
        state = "⚖️ NEUTRAL"
        logic_desc = "Sin anomalía detectada"

        # 1. Debilidad Bajista (Histograma negativo subiendo, sin cruce alcista aún)
        if curr_h < 0 and curr_h > prev_h and curr_m < curr_s:
            state = "📉 PRE-BULLISH"
            logic_desc = "Histograma recuperando. Cruce alcista inminente."
            
        # 2. Debilidad Alcista (Histograma positivo bajando, sin cruce bajista aún)
        elif curr_h > 0 and curr_h < prev_h and curr_m > curr_s:
            state = "📈 PRE-BEARISH"
            logic_desc = "Histograma agotado. Cruce bajista inminente."

        return {
            "Estado 4H": state,
            "Análisis": logic_desc,
            "Hist. Actual": round(curr_h, 6),
            "Hist. Previo": round(prev_h, 6),
            "Precio": f"{df['close'].iloc[-1]:,.4f}"
        }
    except: return None

# ─────────────────────────────────────────────
# MOTOR DE ESCANEO POR LOTES
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    new_data = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando MACD 4H: {sym}")
        res = analyze_macd_pre_cross(sym, ex)
        if res:
            res["Activo"] = sym.split(":")[0].replace("/USDT", "")
            new_data.append(res)
        time.sleep(0.05)
    prog.empty()
    return new_data

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY MACD PRE-CROSS SNIPER")

with st.sidebar:
    st.header("⚙️ Configuración")
    min_vol = st.number_input("Volumen Mínimo 24h (USDT):", value=1000000)
    
    if st.button("📡 1. CARGAR MERCADO"):
        st.session_state["all_symbols"] = fetch_filtered_universe(min_vol)
        st.session_state["pointer"] = 0
        st.success(f"Detectados {len(st.session_state['all_symbols'])} activos líquidos.")

    if st.session_state["all_symbols"]:
        b_size = st.slider("Activos por lote:", 10, 100, 50)
        ptr = st.session_state["pointer"]
        
        if st.button(f"🚀 ESCANEAR LOTE {ptr} a {ptr+b_size}"):
            targets = st.session_state["all_symbols"][ptr : ptr+b_size]
            results = scan_batch(targets)
            
            # Acumular resultados
            existing = {x["Activo"]: x for x in st.session_state["accumulated_results"]}
            for r in results: existing[r["Activo"]] = r
            st.session_state["accumulated_results"] = list(existing.values())
            st.session_state["pointer"] += b_size
            st.rerun()

    if st.button("🗑️ LIMPIAR MEMORIA"):
        st.session_state["accumulated_results"] = []
        st.session_state["pointer"] = 0
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE RESULTADOS
# ─────────────────────────────────────────────
if st.session_state["accumulated_results"]:
    df = pd.DataFrame(st.session_state["accumulated_results"])
    
    # Filtros rápidos
    st.subheader(f"📊 Inteligencia Acumulada ({len(df)} activos)")
    f_estado = st.multiselect("Filtrar por Estado:", options=df["Estado 4H"].unique(), default=df["Estado 4H"].unique())
    df_f = df[df["Estado 4H"].isin(f_estado)]

    def style_macd(val):
        if "PRE-BULLISH" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "PRE-BEARISH" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        return ''

    # Reordenar columnas
    prio = ["Activo", "Estado 4H", "Análisis", "Precio", "Hist. Actual", "Hist. Previo"]
    st.dataframe(df_f[prio].style.map(style_macd, subset=["Estado 4H"]), use_container_width=True, height=600)
    
    csv = df_f.to_csv(index=False)
    st.download_button("📥 Descargar Reporte", csv, "sly_macd_scan.csv", "text/csv")
else:
    st.info("👈 Cargue el mercado e inicie el escaneo para detectar pivotes en 4H.")

with st.expander("📘 MANUAL OPERATIVO (Institutional Pivot)"):
    st.markdown("""
    ### 🎯 LÓGICA DE ENTRADA ANTICIPADA
    *   **📉 PRE-BULLISH:** El histograma está en rojo pero el color se aclara (sube hacia 0). Los vendedores están perdiendo el control. Es el momento donde las instituciones empiezan a acumular (Absorción).
    *   **📈 PRE-BEARISH:** El histograma está en verde pero empieza a caer hacia 0. Los compradores están agotados. Las instituciones empiezan a distribuir (Venta encubierta).
    *   **VENTAJA:** Detectar esto en **4 Horas** te permite entrar antes del cruce oficial de las líneas MACD, mejorando tu Ratio Riesgo/Beneficio.
    """)
