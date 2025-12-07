import streamlit as st

st.set_page_config(
    page_title="SystemaTrader Workstation",
    page_icon="🦅",
    layout="wide"
)

st.title("🦅 SYSTEMATRADER: COMMAND CENTER")
st.markdown("### Infraestructura de Trading Cuantitativo")

st.info("Bienvenido al Panel de Control. Selecciona una herramienta en el MENÚ LATERAL (Izquierda) para comenzar.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("🛠️ Arsenal Disponible")
    st.markdown("""
    *   **📈 Matrix de Tendencias:** Análisis Heikin Ashi Multi-Timeframe.
    *   **🎯 Radar de Oportunidades:** Escáner de Gamma Walls y Max Pain.
    *   **sector Radar Sectorial:** Análisis por grupos (Tech, Argentina, etc).
    *   **📅 Análisis Mensual:** Estacionalidad histórica del Nasdaq/Merval.
    """)

with col2:
    st.subheader("📡 Estado del Sistema")
    st.success("MOTOR: ONLINE")
    st.success("DATOS: CONECTADO")
    st.warning("MODO: INSTITUCIONAL")

st.caption("SystemaTrader Architecture v12.5 | Cloud Deployment")
