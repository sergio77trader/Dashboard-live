import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# (Mantengo el motor de cálculo previo para AL30D)

def show_bond_shield_manual():
    with st.expander("📚 MANUAL DE SUPERVIVENCIA: ¿POR QUÉ MIRAR LOS BONOS?", expanded=False):
        st.markdown("""
        ### 🇦🇷 La Jerarquía de Capital en Argentina
        En un mercado emergente, la deuda (Bonos) es el indicador adelantado de las acciones (Equity). El dinero grande entra y sale primero por los bonos.

        #### 1. Impacto en Acciones Locales (GGAL, YPF, PAMP, etc.)
        *   **Correlación Directa:** Si el Bono (AL30D) cae, el Riesgo País sube. 
        *   **El Efecto:** Los fondos del exterior exigen más retorno para estar en el país, lo que baja automáticamente el valor de las empresas.
        *   **Regla SLY:** Si el *Bond Shield* está en **ROJO**, ignorar señales LONG en acciones locales. Es una trampa de toros.

        #### 2. Impacto en CEDEARs (AAPL, GOOGL, NVDA, etc.)
        *   **El Rol del Dólar:** Cuando los bonos caen, el Dólar CCL suele subir por miedo.
        *   **La Trampa:** Tus CEDEARs pueden subir en pesos solo porque sube el dólar, no porque la empresa sea mejor.
        *   **Regla SLY:** Si el *Bond Shield* está en **ROJO**, el CEDEAR es solo refugio cambiario. Prohibido abrir nuevas posiciones; el costo de oportunidad es muy alto.

        #### 3. El Switch Maestro
        *   🟢 **BOND SHIELD VERDE:** El flujo institucional está entrando al país. Vía libre para máxima exposición en Argentina.
        *   🔴 **BOND SHIELD ROJO:** Fuga de capitales. El sistema ordena **Preservación de Capital**. Ajustar Stop Loss "al cuello".
        """)

# ─────────────────────────────────────────────
# INTEGRACIÓN EN LA INTERFAZ
# ─────────────────────────────────────────────
st.title("📡 SLY | BOND PULSE ENGINE")
st.subheader("Auditoría de Deuda Soberana e Indicador Adelantado")

# Llamada al manual
show_bond_shield_manual()

# ─────────────────────────────────────────────
# RENDERIZADO DE MÉTRICAS (AL30D)
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.info("🇦🇷 **ESTADO DEL SOBERANO (AL30D)**")
    # ... (Cálculos previos de inercia y MACD DEMA) ...
    res_al30 = {"last_price": 58.40, "hist_slope": -0.002, "prev_hist": -0.05} # Ejemplo
    
    st.metric("Precio AL30D", f"USD {res_al30['last_price']:.2f}")
    
    if res_al30['prev_hist'] > 0:
        st.success("✅ BOND SHIELD: ACTIVADO")
    else:
        st.error("❌ BOND SHIELD: DESACTIVADO")

with col2:
    st.markdown("""<div style='background-color:#ECEFF1; padding:15px; border-radius:10px; border-left:5px solid #263238;'>
        <h4 style='margin:0; color:#263238;'>🎯 ORDEN EJECUTIVA</h4>
    </div>""", unsafe_allow_html=True)
    
    if res_al30['prev_hist'] < 0:
        st.warning("⚠️ **ACCIÓN:** El mercado duda de la solvencia. Si tienes acciones argentinas, el riesgo de corrección es del 80%. Protege ganancias en CEDEARs.")
    else:
        st.success("🚀 **ACCIÓN:** El flujo soberano respalda el riesgo. Mantener o cargar activos líderes del Merval.")

st.divider()
st.caption("Arquitectura SLY | Los bonos no mienten, las acciones sí. Audita siempre la deuda antes que el equity.")
