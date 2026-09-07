import streamlit as st
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL MÓDULO MONETARIO
# ─────────────────────────────────────────────
st.title("🏛️ SLY | MONETARY PHYSICS ENGINE")

st.markdown("""
<style>
    .metric-card {
        background-color: #E1F5FE;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0288D1;
        margin-bottom: 20px;
    }
    .status-alert { font-weight: bold; color: #D32F2F; }
    .status-ok { font-weight: bold; color: #388E3C; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INPUTS INSTITUCIONALES (A actualizar según datos del día)
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Variables de BCRA / Mercado")
    ccl_mkt = st.number_input("Dólar CCL Mercado ($):", value=1300.0)
    reservas = st.number_input("Reservas Netas (USD Billones):", value=-5.0)
    pasivos = st.number_input("Base Monetaria + Pasivos ($ Billones):", value=45.0)
    riesgo_pais = st.number_input("Riesgo País (puntos):", value=1500)
    tasa_caucion = st.number_input("Tasa Caución (TNA %):", value=34.0)
    tasa_lecap = st.number_input("Tasa Lecap (TEM %):", value=3.8)

# ─────────────────────────────────────────────
# LÓGICA FORENSE
# ─────────────────────────────────────────────

# 1. Cálculo de Dólar de Respaldo (Física Monetaria)
# Simplificación: Pasivos / Reservas (Si reservas < 0, se usa un multiplicador de estrés)
ccl_teorico = pasivos / (15 if reservas <= 0 else reservas) # Placeholder de ratio de conversión
ccl_ajustado = ccl_mkt * (1 + riesgo_pais / 10000)

# 2. Arbitraje de Tasas
tem_caucion = (tasa_caucion / 365) * 30
diff_tasa = tasa_lecap - tem_caucion

# ─────────────────────────────────────────────
# RENDERIZADO DE ESTRATEGIA DE CAJA
# ─────────────────────────────────────────────

st.subheader("📊 Auditoría de Flujos (Pesos vs Dólar)")

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.write("🟢 **SITUACIÓN DEL DÓLAR**")
    press_ratio = (ccl_mkt / ccl_ajustado - 1) * 100
    st.metric("Brecha vs Dólar Ajustado", f"{press_ratio:.2f}%")
    
    if press_ratio < -5:
        st.markdown('<span class="status-ok">VERDICTO: DÓLAR BARATO. PRIORIDAD CEDEARS/BTC.</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-alert">VERDICTO: DÓLAR EN TENSIÓN. PREFERIR TASA EN PESOS.</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.write("💰 **ARBITRAJE DE TASA CORTA**")
    st.metric("Spread Lecap vs Caución", f"{diff_tasa:.2f}% (TEM)")
    
    if diff_tasa > 0.5:
        st.markdown('<span class="status-ok">VERDICTO: MIGRAR LIQUIDEZ A LETRAS (LECAPS).</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-alert">VERDICTO: QUEDARSE EN CAUCIÓN/FONDO MM (LIQUIDEZ 24H).</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MATRIZ DE DECISIÓN FINAL (THE SCHOOL MODEL)
# ─────────────────────────────────────────────
st.divider()
st.header("🎯 Estrategia de Asignación de Capital")

if press_ratio < -5 and diff_tasa < 0.5:
    st.success("ORDEN: 70% CEDEARS / 30% CAUCIÓN. El dólar está regalado y la tasa no compensa el riesgo de salto.")
elif press_ratio > 0 and diff_tasa > 0.5:
    st.warning("ORDEN: 20% CEDEARS / 80% LECAPS. El dólar está caro. Capturar la tasa real de las letras mientras el CCL lateraliza.")
else:
    st.info("ORDEN: 50% CEDEARS / 50% FONDOS T+1. Incertidumbre en el flujo. Mantener posición neutral equilibrada.")
    # (Añadir este bloque al final del script anterior)

st.divider()
st.subheader("🕵️ Auditoría de Lógica (Verificación Manual)")

with st.expander("Ver fórmulas y cálculos del sistema"):
    st.write(f"""
    1. **Cálculo de Dólar Teórico:** 
       - El sistema toma el CCL de ${ccl_mkt} y le suma la prima por Riesgo País ({riesgo_pais} bps).
       - Resultado: **${ccl_ajustado:,.2f}**. 
       - *Si el mercado está debajo de este valor, el dólar tiene presión alcista oculta.*

    2. **Cálculo de Tasa Mensual (TEM):**
       - TNA Caución {tasa_caucion}% / 365 * 30 = **{tem_caucion:.2f}%**.
       - Comparación vs Lecap ({tasa_lecap}%): Diferencia de **{diff_tasa:.2f}%**.
       - *Si la diferencia es > 0.5%, la Caución es ineficiente.*

    3. **Confluencia Final:**
       - Situación Dólar: {'BARATO' if press_ratio < -5 else 'CARO/TENSO'}
       - Situación Tasa: {'LECAP GANA' if diff_tasa > 0.5 else 'CAUCIÓN/FONDOS OK'}
    """)
