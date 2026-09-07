import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime # Importación robusta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MONETARY ENGINE 2026")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 2px solid #004D40; }
    .metric-card {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #004D40;
        margin-bottom: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    .verdict-box {
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 1.2em;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE CAPTURA DE DATOS EN VIVO
# ─────────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_live_monetary_data():
    # En 2026, el ratio GGAL/ADR sigue siendo el termómetro de liquidez más puro
    tickers = ["GGAL.BA", "GGAL"]
    try:
        data = yf.download(tickers, period="5d", interval="1d", progress=False)['Close']
        # Cálculo de CCL Real (Ratio 1 ADR = 10 Locales)
        ccl_live = (data["GGAL.BA"].iloc[-1] * 10) / data["GGAL"].iloc[-1]
        return float(ccl_live)
    except:
        return 1300.0 # Fallback de seguridad en caso de error de API

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
now = datetime.datetime.now() # Referencia de tiempo corregida
st.title("🏛️ SLY | MONETARY PHYSICS ENGINE")
st.write(f"**AUDITORÍA DE FLUJOS - FECHA PROCESAMIENTO:** {now.strftime('%d/%m/%Y %H:%M')}")

live_ccl = fetch_live_monetary_data()

with st.sidebar:
    st.header("⚙️ Variables de Mercado 2026")
    ccl_mkt = st.number_input("Dólar CCL Mercado ($):", value=live_ccl)
    riesgo_pais = st.number_input("Riesgo País (bps):", value=1200)
    
    st.divider()
    st.subheader("Tasas de Interés")
    tasa_caucion = st.number_input("Tasa Caución (TNA %):", value=38.0)
    tasa_lecap = st.number_input("Tasa Letra/Lefi (TEM %):", value=3.5)

# ─────────────────────────────────────────────
# LÓGICA FORENSE
# ─────────────────────────────────────────────

# 1. Cálculo de Dólar de Equilibrio (Ajuste por Riesgo)
# Fórmula: CCL * (1 + Riesgo/10000)
ccl_ajustado = ccl_mkt * (1 + riesgo_pais / 10000)
press_ratio = (ccl_mkt / ccl_ajustado - 1) * 100

# 2. Arbitraje de Tasas (Normalización a TEM)
tem_caucion = (tasa_caucion / 365) * 30
diff_tasa = tasa_lecap - tem_caucion

# ─────────────────────────────────────────────
# VISUALIZACIÓN DE DIMENSIONES
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.write("🟢 **DIMENSIÓN 1: EL PRECIO DEL DÓLAR**")
    st.metric("Brecha vs Dólar de Equilibrio", f"{press_ratio:.2f}%")
    
    if press_ratio < -5:
        st.success("VERDICTO: DÓLAR SUBVALUADO")
    elif press_ratio > 2:
        st.error("VERDICTO: DÓLAR SOBREVALUADO")
    else:
        st.warning("VERDICTO: DÓLAR EN EQUILIBRIO")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.write("💰 **DIMENSIÓN 2: EL COSTO DE OPORTUNIDAD**")
    st.metric("Diferencial TEM (Letra vs Caución)", f"{diff_tasa:.2f}%")
    
    if diff_tasa > 0.4:
        st.success("VERDICTO: EFICIENCIA EN LETRAS")
    else:
        st.info("VERDICTO: EFICIENCIA EN CAUCIÓN")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# AUDITORÍA DE LÓGICA (EL "POR QUÉ")
# ─────────────────────────────────────────────
st.divider()
st.subheader("🕵️ Auditoría de Lógica (Verificación Manual)")

with st.expander("Ver fórmulas y desgloses de este análisis"):
    st.markdown(f"""
    ### 1. El Dólar de Equilibrio
    En septiembre de 2026, el dólar no es solo un precio, es una prima de riesgo.
    *   **Fórmula:** `CCL Mercado * (1 + (Riesgo País / 10.000))`
    *   **Cálculo actual:** `{ccl_mkt} * (1 + {riesgo_pais/10000})` = **${ccl_ajustado:,.2f}**
    *   **Interpretación:** Si el precio actual (${ccl_mkt}) está debajo de su equilibrio teórico, los activos dolarizados (CEDEARs) tienen un margen de seguridad implícito.

    ### 2. El Arbitraje de Tasa
    Comparamos la liquidez inmediata (Caución) vs la inversión de tesorería (Letras).
    *   **TEM Caución:** `({tasa_caucion}% / 365 * 30)` = **{tem_caucion:.2f}%**.
    *   **TEM Letra:** **{tasa_lecap:.2f}%**.
    *   **Spread:** **{diff_tasa:.2f}%**. 
    *   **Interpretación:** Si el spread es > 0.4%, el sistema penaliza la inacción. Dejar capital en fondos T+0 es perder Alpha.
    """)

# ─────────────────────────────────────────────
# ESTRATEGIA FINAL
# ─────────────────────────────────────────────
st.divider()
st.subheader("🎯 Orden Ejecutiva del Sistema")

if press_ratio < -5 and diff_tasa < 0.4:
    msg = "ACCIONAR: 80% RENTA VARIABLE (CEDEAR/BTC) / 20% CAUCIÓN. El dólar está barato respecto al riesgo país."
    st.markdown(f'<div class="verdict-box" style="background-color:#C8E6C9; color:#1B5E20;">{msg}</div>', unsafe_allow_html=True)
elif press_ratio > 0 and diff_tasa > 0.4:
    msg = "ACCIONAR: 20% RENTA VARIABLE / 80% LETRAS (LECAP). Capturar tasa real mientras el dólar descansa."
    st.markdown(f'<div class="verdict-box" style="background-color:#FFF9C4; color:#827717;">{msg}</div>', unsafe_allow_html=True)
else:
    msg = "ACCIONAR: POSICIÓN NEUTRAL (50/50). Esperar señales claras en la Matrix Técnica."
    st.markdown(f'<div class="verdict-box" style="background-color:#E3F2FD; color:#0D47A1;">{msg}</div>', unsafe_allow_html=True)
