import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(layout="wide", page_title="SLY | ALPHA GRINDER v2.0")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1E88E5; font-weight: 800; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #1E88E5; color: white; border: none; }
    .stButton>button:hover { background-color: #1565C0; color: white; }
    .status-msg { padding: 15px; border-radius: 10px; background-color: #e3f2fd; color: #0d47a1; margin-bottom: 20px; border: 1px solid #bbdefb; }
    .metric-box { padding: 10px; border-radius: 10px; background: white; border: 1px solid #ddd; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA (PERSISTENCIA TOTAL) ---
if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []
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
        # Filtramos pares USDT activos
        symbols = [s for s in markets if '/USDT' in s and markets[s].get('active', True)]
        return sorted(symbols)
    except Exception as e:
        st.error(f"Fallo de conexión: {e}")
        return []

# --- LÓGICA DE DECISIÓN ---
def get_recommendation(delta):
    if delta > 4: return "🔥 ALPHA STRIKE", "Fuerza excepcional. Atleta olímpico."
    if delta > 1: return "🏃 CORREDOR", "Más rápido que el tren."
    if delta > -1: return "⚖️ NEUTRAL", "Al ritmo de Bitcoin."
    return "🐢 LENTO", "Bitcoin es más rápido. Evitar."

# --- INTERFAZ DE MANDO ---
st.title("🛡️ SLY Alpha Grinder v2.0")
st.markdown(f'<div class="status-msg">Estado: Escaneo acumulativo por lotes activo. Datos vía <b>KuCoin</b>.</div>', unsafe_allow_html=True)

# 1. Cargar el universo si está vacío
if not st.session_state["all_symbols"]:
    if st.button("📡 PASO 1: CARGAR UNIVERSO DE MONEDAS"):
        st.session_state["all_symbols"] = fetch_universe()
        st.rerun()

# 2. Operación por Lotes
if st.session_state["all_symbols"]:
    total_assets = len(st.session_state["all_symbols"])
    pointer = st.session_state["current_pointer"]
    
    # Dashboard de Progreso
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(f'<div class="metric-box"><b>Total Universo</b><br><span style="font-size:20px;">{total_assets}</span></div>', unsafe_allow_html=True)
    with col_info2:
        st.markdown(f'<div class="metric-box"><b>Ya Escaneadas</b><br><span style="font-size:20px; color:#1E88E5;">{pointer}</span></div>', unsafe_allow_html=True)
    with col_info3:
        pendientes = total_assets - pointer
        st.markdown(f'<div class="metric-box"><b>Pendientes</b><br><span style="font-size:20px;">{pendientes}</span></div>', unsafe_allow_html=True)

    st.divider()
    
    # Configuración del lote
    batch_size = st.slider("Monedas por lote:", 10, 100, 50)
    
    next_limit = min(pointer + batch_size, total_assets)
    
    if pointer < total_assets:
        if st.button(f"🚀 ESCANEAR LOTE: {pointer} al {next_limit}"):
            ex = get_exchange()
            targets = st.session_state["all_symbols"][pointer:next_limit]
            
            # 1. Obtener Benchmark (BTC)
            try:
                btc_t = ex.fetch_ticker('BTC/USDT')
                btc_perf = btc_t.get('percentage', 0)
                
                new_batch = []
                prog_bar = st.progress(0)
                status_text = st.empty()

                for i, sym in enumerate(targets):
                    status_text.text(f"Analizando {sym}...")
                    try:
                        t = ex.fetch_ticker(sym)
                        alt_perf = t.get('percentage', 0)
                        if alt_perf is None: continue
                        
                        delta = alt_perf - btc_perf
                        rec, logic = get_recommendation(delta)
                        
                        new_batch.append({
                            "Activo": sym.replace("/USDT", ""),
                            "Precio": f"${t.get('last', 0):,.4f}",
                            "Rend. 24h": f"{alt_perf:+.2f}%",
                            "Vs BTC (Delta)": round(delta, 2),
                            "RECOMENDACIÓN": rec,
                            "Explicación": logic
                        })
                    except: continue
                    prog_bar.progress((i + 1) / len(targets))
                    time.sleep(0.05) # Jitter para evitar Rate Limit
                
                # Acumular y actualizar puntero
                if new_batch:
                    df_new = pd.DataFrame(new_batch)
                    st.session_state["accumulated_data"] = pd.concat([st.session_state["accumulated_data"], df_new]).drop_duplicates(subset="Activo")
                    st.session_state["current_pointer"] = next_limit
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Fallo en el lote: {e}")
    else:
        st.success("🎯 ¡Todo el universo ha sido escaneado!")

# --- TABLA DE RESULTADOS ACUMULADOS ---
if not st.session_state["accumulated_data"].empty:
    st.divider()
    st.subheader(f"📊 Inteligencia Acumulada ({len(st.session_state['accumulated_data'])} activos)")
    
    # Ordenar por el que más le gana a BTC
    df_display = st.session_state["accumulated_data"].sort_values(by="Vs BTC (Delta)", ascending=False)
    
    def style_delta(val):
        color = '#1b5e20' if val > 0 else '#b71c1c'
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        df_display.style.applymap(style_delta, subset=['Vs BTC (Delta)']),
        use_container_width=True,
        height=600
    )

    col_foot1, col_foot2 = st.columns(2)
    with col_foot1:
        if st.button("🗑️ REINICIAR TODO (Limpiar Memoria)"):
            st.session_state["accumulated_data"] = pd.DataFrame()
            st.session_state["current_pointer"] = 0
            st.rerun()
    with col_foot2:
        csv = df_display.to_csv(index=False)
        st.download_button("📥 DESCARGAR INFORME ALPHA", csv, "alpha_report.csv", "text/csv")

else:
    st.info("Utiliza el botón de arriba para comenzar a acumular datos de fuerza relativa.")
