import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(layout="wide", page_title="SLY | ALPHA ACCUMULATOR")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #2962FF; font-weight: 800; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; background-color: #2962FF; color: white; }
    .status-msg { padding: 10px; border-radius: 5px; background-color: #e3f2fd; color: #0d47a1; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- MEMORIA DE ESTADO ---
if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []

# --- MOTOR DE DATOS (KUCOIN - ANTI BLOCK) ---
@st.cache_resource
def get_exchange():
    # Usamos KuCoin porque no bloquea las IPs de Streamlit Cloud
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 30000})

def fetch_universe():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        # Filtramos pares con USDT que estén activos
        symbols = [s for s in markets if '/USDT' in s and markets[s].get('active', True)]
        return sorted(symbols)
    except Exception as e:
        st.error(f"Error al cargar mercados: {e}")
        return []

# --- LÓGICA DE RECOMENDACIÓN ---
def get_recommendation(delta):
    if delta > 5: return "🚀 ALPHA STRIKE", "Fuerza extrema. Corre mucho más que Bitcoin."
    if delta > 1: return "🏃 CORREDOR RÁPIDO", "Superior a Bitcoin en este momento."
    if delta > -1: return "⚖️ RITMO DE TREN", "Sincronizado con Bitcoin."
    return "🐢 LENTO / EVITAR", "Bitcoin es más rápido. Riesgo innecesario."

# --- INTERFAZ ---
st.title("🛡️ Alpha Accumulator v1.1")
st.markdown('<div class="status-msg">Motor de Datos: <b>KuCoin Global</b> (Bypass de Restricciones Activo)</div>', unsafe_allow_html=True)

if st.button("📡 1. CARGAR UNIVERSO DE MONEDAS"):
    st.session_state["all_symbols"] = fetch_universe()
    if st.session_state["all_symbols"]:
        st.success(f"Detectados {len(st.session_state['all_symbols'])} activos en KuCoin.")

if st.session_state["all_symbols"]:
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        batch_size = st.number_input("Tamaño del lote:", value=20, step=10) # Lote más pequeño para estabilidad
    with col_ctrl2:
        total_scanned = len(st.session_state["accumulated_data"])
        start_idx = st.number_input("Empezar desde el índice:", value=total_scanned)

    if st.button(f"🚀 2. ESCANEAR PRÓXIMAS {batch_size} MONEDAS"):
        ex = get_exchange()
        end_idx = min(start_idx + batch_size, len(st.session_state["all_symbols"]))
        targets = st.session_state["all_symbols"][start_idx:end_idx]
        
        with st.spinner(f"Analizando bloque {start_idx} a {end_idx}..."):
            try:
                # Obtener rendimiento de BTC como benchmark
                btc_t = ex.fetch_ticker('BTC/USDT')
                btc_perf = btc_t.get('percentage', 0)
                
                new_results = []
                for sym in targets:
                    try:
                        t = ex.fetch_ticker(sym)
                        alt_perf = t.get('percentage', 0)
                        if alt_perf is None: continue
                        
                        delta = alt_perf - btc_perf
                        rec, logic = get_recommendation(delta)
                        
                        new_results.append({
                            "Activo": sym.replace("/USDT", ""),
                            "Precio": t.get('last', 0),
                            "Cambio 24h": f"{alt_perf:+.2f}%",
                            "Vs BTC (Delta)": round(delta, 2),
                            "RECOMENDACIÓN": rec,
                            "Análisis": logic
                        })
                        time.sleep(0.1) # Evitar spam a la API
                    except: continue
                
                df_new = pd.DataFrame(new_results)
                if not df_new.empty:
                    st.session_state["accumulated_data"] = pd.concat([st.session_state["accumulated_data"], df_new]).drop_duplicates(subset="Activo")
                st.rerun()
            except Exception as e:
                st.error(f"Error en escaneo: {e}")

# --- TABLA DE RESULTADOS ---
if not st.session_state["accumulated_data"].empty:
    st.divider()
    st.subheader(f"📊 Hallazgos Acumulados ({len(st.session_state['accumulated_data'])} activos)")
    
    df_display = st.session_state["accumulated_data"].copy()
    
    def color_delta(val):
        color = '#188038' if val > 0 else '#d93025'
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df_display.style.applymap(color_delta, subset=['Vs BTC (Delta)']),
        use_container_width=True,
        height=500
    )

    if st.button("🗑️ REINICIAR RADAR"):
        st.session_state["accumulated_data"] = pd.DataFrame()
        st.rerun()
