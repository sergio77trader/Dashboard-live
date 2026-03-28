import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(layout="wide", page_title="SLY | BATCH ACCUMULATOR")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #002d5a; font-weight: 800; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA (SESSION STATE) ---
if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []

# --- MOTOR DE DATOS ---
@st.cache_resource
def get_exchange():
    return ccxt.binance({"enableRateLimit": True})

def fetch_universe():
    ex = get_exchange()
    markets = ex.load_markets()
    # Filtramos solo Futuros Perpetuos para mayor liquidez, o Spot si prefieres.
    # Aquí usamos pares con USDT.
    symbols = [s for s in markets if '/USDT' in s and markets[s]['active']]
    return sorted(symbols)

# --- LÓGICA DE RECOMENDACIÓN ---
def get_recommendation(delta):
    if delta > 5: return "🚀 ALPHA STRIKE", "Este niño es un atleta olímpico. Corre muchísimo más que el tren."
    if delta > 1: return "🏃 CORREDOR RÁPIDO", "Va más rápido que el tren. Es buena idea seguirlo."
    if delta > -1: return "⚖️ RITMO DE TREN", "Va a la misma velocidad que Bitcoin. No hay ventaja extra."
    return "🐢 LENTO / EVITAR", "Se está quedando atrás. Mejor quédate sentado en el tren (BTC)."

# --- INTERFAZ DE USUARIO ---
st.title("🛡️ Alpha Accumulator: BTC Relative Strength")
st.write("Escanea el mercado por lotes y acumula las mejores oportunidades.")

# Botón inicial para cargar el universo
if st.button("📡 CARGAR UNIVERSO DE MONEDAS (BINANCE)"):
    st.session_state["all_symbols"] = fetch_universe()
    st.success(f"Universo cargado: {len(st.session_state['all_symbols'])} activos detectados.")

if st.session_state["all_symbols"]:
    # Controles de lotes
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        batch_size = st.number_input("Tamaño del lote:", value=50, step=10)
    with col_ctrl2:
        total_scanned = len(st.session_state["accumulated_data"])
        start_idx = st.number_input("Empezar desde el índice:", value=total_scanned, step=batch_size)

    if st.button(f"🚀 ESCANEAR PRÓXIMAS {batch_size} MONEDAS"):
        ex = get_exchange()
        end_idx = min(start_idx + batch_size, len(st.session_state["all_symbols"]))
        targets = st.session_state["all_symbols"][start_idx:end_idx]
        
        with st.spinner(f"Analizando {start_idx} a {end_idx}..."):
            # 1. Obtener rendimiento de BTC
            btc_ticker = ex.fetch_ticker('BTC/USDT')
            btc_perf = btc_ticker['percentage']
            
            new_results = []
            for sym in targets:
                try:
                    t = ex.fetch_ticker(sym)
                    alt_perf = t['percentage']
                    delta = alt_perf - btc_perf
                    rec, logic = get_recommendation(delta)
                    
                    new_results.append({
                        "Activo": sym.replace("/USDT", ""),
                        "Precio": t['last'],
                        "Cambio 24h": f"{alt_perf:+.2f}%",
                        "Vs BTC (Delta)": delta,
                        "RECOMENDACIÓN": rec,
                        "Explicación": logic
                    })
                except: continue
            
            # Acumular en memoria
            df_new = pd.DataFrame(new_results)
            st.session_state["accumulated_data"] = pd.concat([st.session_state["accumulated_data"], df_new]).drop_duplicates(subset="Activo")
            st.rerun()

# --- RENDERIZADO DE TABLA ACUMULADA ---
if not st.session_state["accumulated_data"].empty:
    st.divider()
    st.subheader(f"📊 Resultados Acumulados ({len(st.session_state['accumulated_data'])} activos)")
    
    # Filtros de tabla
    df_display = st.session_state["accumulated_data"].copy()
    
    # Estilo de colores
    def style_delta(val):
        color = '#188038' if val > 0 else '#d93025'
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df_display.style.applymap(style_delta, subset=['Vs BTC (Delta)']),
        use_container_width=True,
        height=500
    )

    col_footer1, col_footer2 = st.columns(2)
    with col_footer1:
        if st.button("🗑️ LIMPIAR MEMORIA"):
            st.session_state["accumulated_data"] = pd.DataFrame()
            st.rerun()
    with col_footer2:
        st.download_button("📥 DESCARGAR CSV", df_display.to_csv(index=False), "alpha_scan.csv")

# --- EXPLICACIÓN PARA EL NIÑO ---
with st.expander("🧒 EXPLICACIÓN: El Juego del Tren (Recordatorio)"):
    st.info("""
    **Bitcoin es el Tren.** Las demás monedas son **niños corriendo.**
    
    *   **Delta Positivo (+):** El niño corre más rápido que el tren. ¡Te conviene subirte al niño!
    *   **Delta Negativo (-):** El tren va más rápido. No pierdas tiempo con el niño, quédate en el Tren (BTC).
    """)
