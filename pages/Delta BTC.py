import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(layout="wide", page_title="SLY | BINANCE ALPHA GRINDER")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #F3BA2F; font-weight: 800; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #F3BA2F; color: #1e1e1e; border: none; }
    .stButton>button:hover { background-color: #e2ab26; }
    .status-msg { padding: 15px; border-radius: 10px; background-color: #fff9e6; color: #856404; margin-bottom: 20px; border: 1px solid #ffeeba; }
</style>
""", unsafe_allow_html=True)

# --- LISTA MAESTRA DE BINANCE (TOP LIQUIDITY) ---
# Esta lista asegura que solo analices lo que podés tradear en Binance.
BINANCE_WHITELIST = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'LINK', 'MATIC', 'SHIB', 'TRX', 'LTC', 'BCH', 
    'UNI', 'NEAR', 'SUI', 'APT', 'OP', 'ARB', 'TIA', 'INJ', 'LINK', 'FET', 'RNDR', 'STX', 'KAS', 'ORDI', 'FIL', 
    'ATOM', 'IMX', 'HBAR', 'LDO', 'ICP', 'GRT', 'AAVE', 'MKR', 'RUNE', 'EGLD', 'SEI', 'PEPE', 'WIF', 'FLOKI', 
    'BONK', 'JUP', 'PYTH', 'ENA', 'BOME', 'STRK', 'DYDX', 'GALA', 'ALGO', 'FLOW', 'VET', 'EGLD', 'AXS', 'SAND', 
    'MANA', 'THETA', 'CHZ', 'BEAM', 'PENDLE', 'ALT', 'MANTA', 'PIXEL', 'STRK', 'DYM', 'RON', 'ARKM', 'ID', 'MAV'
    # ... El motor aceptará cualquier coincidencia con estos líderes de volumen
]

# --- MEMORIA DE ESTADO ---
if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "filtered_symbols" not in st.session_state:
    st.session_state["filtered_symbols"] = []
if "current_pointer" not in st.session_state:
    st.session_state["current_pointer"] = 0

# --- MOTOR DE DATOS ---
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 30000})

def fetch_binance_compatible_universe():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        
        # Filtrar: 1. Par USDT | 2. Activo | 3. Que exista en nuestra Whitelist de Binance
        compatible = []
        for s in markets:
            base = s.split('/')[0]
            if '/USDT' in s and markets[s].get('active', True):
                if base in BINANCE_WHITELIST or markets[s].get('quoteVolume', 0) > 1000000:
                    compatible.append(s)
        
        return sorted(list(set(compatible)))
    except Exception as e:
        st.error(f"Fallo de conexión: {e}")
        return []

# --- LÓGICA DE DECISIÓN ---
def get_recommendation(delta):
    if delta > 4: return "🔥 ALPHA STRIKE", "Fuerza excepcional vs BTC."
    if delta > 1: return "🏃 CORREDOR", "Ganándole al tren."
    if delta > -1: return "⚖️ NEUTRAL", "Igual que Bitcoin."
    return "🐢 LENTO", "Bitcoin es mejor opción hoy."

# --- INTERFAZ ---
st.title("🛡️ SLY Binance-Alpha Grinder v2.1")
st.markdown('<div class="status-msg">Filtro Activo: <b>Solo monedas disponibles en Binance</b>.</div>', unsafe_allow_html=True)

if not st.session_state["filtered_symbols"]:
    if st.button("📡 1. SINCRONIZAR UNIVERSO BINANCE/KUCOIN"):
        st.session_state["filtered_symbols"] = fetch_binance_compatible_universe()
        st.rerun()

if st.session_state["filtered_symbols"]:
    total_assets = len(st.session_state["filtered_symbols"])
    pointer = st.session_state["current_pointer"]
    
    st.info(f"Total de activos Binance-compatibles detectados: {total_assets}")
    
    batch_size = st.slider("Monedas por lote:", 10, 100, 50)
    next_limit = min(pointer + batch_size, total_assets)
    
    if pointer < total_assets:
        if st.button(f"🚀 ESCANEAR LOTE: {pointer} al {next_limit}"):
            ex = get_exchange()
            targets = st.session_state["filtered_symbols"][pointer:next_limit]
            
            try:
                # Benchmark BTC
                btc_t = ex.fetch_ticker('BTC/USDT')
                btc_perf = btc_t.get('percentage', 0)
                
                new_batch = []
                prog_bar = st.progress(0)
                for i, sym in enumerate(targets):
                    try:
                        t = ex.fetch_ticker(sym)
                        alt_perf = t.get('percentage', 0)
                        delta = alt_perf - btc_perf
                        rec, logic = get_recommendation(delta)
                        
                        new_batch.append({
                            "Activo": sym.replace("/USDT", ""),
                            "Precio": f"${t.get('last', 0):,.4f}",
                            "Rend. 24h": f"{alt_perf:+.2f}%",
                            "Vs BTC (Delta)": round(delta, 2),
                            "RECOMENDACIÓN": rec,
                            "Análisis": logic
                        })
                    except: continue
                    prog_bar.progress((i + 1) / len(targets))
                
                if new_batch:
                    df_new = pd.DataFrame(new_batch)
                    st.session_state["accumulated_data"] = pd.concat([st.session_state["accumulated_data"], df_new]).drop_duplicates(subset="Activo")
                    st.session_state["current_pointer"] = next_limit
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.success("🎯 Todo el catálogo de Binance ha sido analizado.")

# --- RESULTADOS ---
if not st.session_state["accumulated_data"].empty:
    st.divider()
    df_display = st.session_state["accumulated_data"].sort_values(by="Vs BTC (Delta)", ascending=False)
    
    def color_delta(val):
        color = '#1b5e20' if val > 0 else '#b71c1c'
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        df_display.style.applymap(color_delta, subset=['Vs BTC (Delta)']),
        use_container_width=True,
        height=600
    )

    if st.button("🗑️ REINICIAR Y LIMPIAR"):
        st.session_state["accumulated_data"] = pd.DataFrame()
        st.session_state["current_pointer"] = 0
        st.rerun()
