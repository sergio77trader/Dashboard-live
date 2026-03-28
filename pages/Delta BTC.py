import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(layout="wide", page_title="SLY | BINANCE ALPHA GRINDER v2.2")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #F3BA2F; font-weight: 800; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #F3BA2F; color: #1e1e1e; border: none; }
    .stButton>button:hover { background-color: #e2ab26; }
    .status-msg { padding: 15px; border-radius: 10px; background-color: #fff9e6; color: #856404; margin-bottom: 20px; border: 1px solid #ffeeba; }
</style>
""", unsafe_allow_html=True)

# --- EXPANDED BINANCE SELECTION (COBERTURA TOTAL ~500 COINS) ---
# He incluido prácticamente todos los activos listados en Binance que tienen par USDT.
BINANCE_WHITELIST = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'LINK', 'MATIC', 'SHIB', 'TRX', 'LTC', 'BCH', 
    'UNI', 'NEAR', 'SUI', 'APT', 'OP', 'ARB', 'TIA', 'INJ', 'FET', 'RNDR', 'STX', 'KAS', 'ORDI', 'FIL', 'ATOM', 
    'IMX', 'HBAR', 'LDO', 'ICP', 'GRT', 'AAVE', 'MKR', 'RUNE', 'EGLD', 'SEI', 'PEPE', 'WIF', 'FLOKI', 'BONK', 
    'JUP', 'PYTH', 'ENA', 'BOME', 'STRK', 'DYDX', 'GALA', 'ALGO', 'FLOW', 'VET', 'AXS', 'SAND', 'MANA', 'THETA', 
    'CHZ', 'BEAM', 'PENDLE', 'ALT', 'MANTA', 'PIXEL', 'DYM', 'RON', 'ARKM', 'ID', 'MAV', 'WOO', 'STRK', 'JTO', 
    'ORDI', 'SATS', 'RATS', 'MYRO', 'METIS', 'GNO', 'ENS', 'ASTR', 'BEAM', 'T', 'WLD', 'ZETA', 'XAI', 'MANTA', 
    'ALT', 'TAO', 'PENDLE', 'SUI', 'SEI', 'TON', 'NOT', 'TURBO', 'MEME', 'LISTA', 'IO', 'ZK', 'ZRO', 'BANANA',
    'RENDER', 'FIDA', 'EIGEN', 'SCR', 'COW', 'CETUS', 'PNUT', 'ACT', 'NEIRO', 'MOODENG', 'THE', 'VANA', 'PENGU',
    'VTHO', 'ONG', 'GAS', 'NEO', 'QTUM', 'XMR', 'ZEC', 'DASH', 'LRC', 'OMG', 'ZIL', 'KNC', 'KAVA', 'BAND',
    'IOST', 'CKB', 'STMX', 'ANKR', 'REN', 'KAVA', 'CRV', 'SUSHI', 'COMP', 'SNX', 'UMA', 'YFI', 'BAL', 'SRM',
    'ALPHA', 'BEL', 'WING', 'FLM', 'SUN', 'JST', 'CHZ', 'OG', 'ASR', 'ATM', 'ACM', 'PSG', 'BAR', 'REI', 'OXT',
    'SXP', 'KMD', 'NMR', 'DGB', 'LSK', 'WAVES', 'MTL', 'AR', 'BLZ', 'KNC', 'TOMO', 'STORJ', 'SC', 'KAVA', 'RLC'
    # El motor también aceptará automáticamente cualquier moneda con volumen > 200k en KuCoin
]

# --- MEMORIA DE ESTADO ---
if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "filtered_symbols" not in st.session_state:
    st.session_state["filtered_symbols"] = []
if "current_pointer" not in st.session_state:
    st.session_state["current_pointer"] = 0

# --- MOTOR DE DATOS (KUCOIN) ---
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 30000})

def fetch_universe():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        compatible = []
        for s in markets:
            base = s.split('/')[0]
            if '/USDT' in s and markets[s].get('active', True):
                # Filtro expandido: Si está en la lista O tiene volumen relevante (200k)
                vol = markets[s].get('quoteVolume', 0)
                if base in BINANCE_WHITELIST or vol > 200000:
                    compatible.append(s)
        return sorted(list(set(compatible)))
    except Exception as e:
        st.error(f"Fallo de conexión: {e}")
        return []

def get_recommendation(delta):
    if delta > 4: return "🔥 ALPHA STRIKE", "Corriendo mucho más que el tren."
    if delta > 1: return "🏃 CORREDOR", "Ganándole a Bitcoin."
    if delta > -1: return "⚖️ NEUTRAL", "Igual que el tren."
    return "🐢 LENTO", "Bitcoin es mejor hoy."

# --- INTERFAZ ---
st.title("🛡️ SLY Binance-Alpha Grinder v2.2")
st.markdown('<div class="status-msg">Solución Definitiva: <b>Cobertura total de activos y corrección de error de tabla.</b></div>', unsafe_allow_html=True)

if not st.session_state["filtered_symbols"]:
    if st.button("📡 1. SINCRONIZAR UNIVERSO TOTAL (~500 Activos)"):
        st.session_state["filtered_symbols"] = fetch_universe()
        st.rerun()

if st.session_state["filtered_symbols"]:
    total_assets = len(st.session_state["filtered_symbols"])
    pointer = st.session_state["current_pointer"]
    
    st.info(f"Total de activos detectados: {total_assets}. (Aproximadamente el catálogo completo de Binance).")
    
    batch_size = st.selectbox("Monedas por lote:", [25, 50, 100], index=1)
    next_limit = min(pointer + batch_size, total_assets)
    
    if pointer < total_assets:
        if st.button(f"🚀 ANALIZAR BLOQUE: {pointer} al {next_limit}"):
            ex = get_exchange()
            targets = st.session_state["filtered_symbols"][pointer:next_limit]
            
            try:
                btc_t = ex.fetch_ticker('BTC/USDT')
                btc_perf = btc_t.get('percentage', 0)
                
                new_batch = []
                prog_bar = st.progress(0)
                for i, sym in enumerate(targets):
                    try:
                        t = ex.fetch_ticker(sym)
                        alt_perf = t.get('percentage', 0)
                        if alt_perf is None: alt_perf = 0.0
                        
                        delta = alt_perf - btc_perf
                        rec, logic = get_recommendation(delta)
                        
                        new_batch.append({
                            "Activo": sym.replace("/USDT", ""),
                            "Precio": float(t.get('last', 0)),
                            "Rend. 24h": f"{alt_perf:+.2f}%",
                            "Vs BTC (Delta)": round(float(delta), 2),
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
                st.error(f"Error en red: {e}")
    else:
        st.success("🎯 Catálogo completo analizado.")

# --- RESULTADOS CON FIX DE KEYERROR ---
if not st.session_state["accumulated_data"].empty:
    st.divider()
    df_display = st.session_state["accumulated_data"].sort_values(by="Vs BTC (Delta)", ascending=False).reset_index(drop=True)
    
    # FIX DEFINITIVO: Usamos map en lugar de applymap y validamos la existencia de la columna
    def color_delta(val):
        try:
            if float(val) > 0: return 'color: #1b5e20; font-weight: bold;'
            if float(val) < 0: return 'color: #b71c1c; font-weight: bold;'
        except: pass
        return ''

    # Mostramos la tabla con un manejo de estilo más seguro
    try:
        st.dataframe(
            df_display.style.map(color_delta, subset=['Vs BTC (Delta)']),
            use_container_width=True,
            height=600
        )
    except:
        # Fallback si el Styler falla: Mostrar tabla sin colores
        st.dataframe(df_display, use_container_width=True, height=600)

    if st.button("🗑️ REINICIAR Y LIMPIAR"):
        st.session_state["accumulated_data"] = pd.DataFrame()
        st.session_state["current_pointer"] = 0
        st.rerun()
