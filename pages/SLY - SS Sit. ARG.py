import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE SEGURIDAD
# ─────────────────────────────────────────────
PASSWORD_MAESTRA = "SLY2026"

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 ACCESO RESTRINGIDO | SLY ENGINE")
        input_pass = st.text_input("Ingrese Credencial de Operador:", type="password")
        if st.button("Desbloquear Sistema"):
            if input_pass == PASSWORD_MAESTRA:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Credencial Incorrecta.")
        return False
    return True

if check_password():
    st.set_page_config(layout="wide", page_title="SLY | MONETARY ENGINE 2026")

    st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; color: #1C1E21; }
        h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #004D40; }
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
        .math-box {
            background-color: #FFFDE7;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #FBC02D;
            font-family: 'Courier New', monospace;
        }
    </style>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # MOTOR DE CAPTURA DE DATOS (EL DETECTOR DE LA VERDAD)
    # ─────────────────────────────────────────────
    @st.cache_data(ttl=60)
    def fetch_market_prices():
        try:
            # Descargamos GGAL local y ADR
            data = yf.download(["GGAL.BA", "GGAL"], period="1d", progress=False)['Close']
            local = data["GGAL.BA"].iloc[-1]
            adr = data["GGAL"].iloc[-1]
            return local, adr
        except:
            return 6930.0, 44.36 # Valores que me pasaste como respaldo

    st.title("🏛️ SLY | MONETARY PHYSICS ENGINE")
    st.write(f"**AUDITORÍA TÉCNICA AL:** 07/09/2026")

    l_px, a_px = fetch_market_prices()

    with st.sidebar:
        st.header("⚙️ Entradas de Mercado")
        st.subheader("Cálculo de Dólar Implícito")
        # El usuario puede corregir los valores si el API tiene delay
        local_in = st.number_input("GGAL Local (ARS):", value=float(l_px), step=1.0)
        adr_in = st.number_input("GGAL ADR (USD):", value=float(a_px), step=0.01)
        
        # El ratio es 10 a 1 para GGAL
        ccl_calculado = (local_in * 10) / adr_in
        
        st.markdown(f"""
        <div class='math-box'>
        <b>Cálculo CCL:</b><br>
        ({local_in} * 10) / {adr_in} = <br>
        <b>${ccl_calculado:.2f}</b>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        riesgo_pais = st.number_input("Riesgo País (bps):", value=490)
        tasa_caucion = st.number_input("Tasa Caución (TNA %):", value=19.10)
        tasa_lecap = st.number_input("Tasa Letra (TEM %):", value=1.95)
        
        if st.button("🔒 Cerrar Sesión"):
            st.session_state["authenticated"] = False
            st.rerun()

    # ─────────────────────────────────────────────
    # LÓGICA DE FÍSICA MONETARIA
    # ─────────────────────────────────────────────
    
    # 1. Dólar de Equilibrio (Ajustado por Riesgo)
    ccl_teorico = ccl_calculado * (1 + riesgo_pais / 10000)
    press_ratio = (ccl_calculado / ccl_teorico - 1) * 100

    # 2. Arbitraje de Tasas
    tem_caucion = (tasa_caucion / 365) * 30
    diff_tasa = tasa_lecap - tem_caucion

    # ─────────────────────────────────────────────
    # VISUALIZACIÓN
    # ─────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("🟢 **DIMENSIÓN 1: PRECIO DEL DÓLAR**")
        st.metric("CCL de Mercado", f"${ccl_calculado:.2f}")
        st.metric("Brecha vs Dólar de Equilibrio", f"{press_ratio:.2f}%")
        
        if press_ratio < -4:
            st.success("VERDICTO: DÓLAR SUBVALUADO (BARATO)")
        elif press_ratio > 1:
            st.error("VERDICTO: DÓLAR SOBREVALUADO (CARO)")
        else:
            st.warning("VERDICTO: DÓLAR EN EQUILIBRIO")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("💰 **DIMENSIÓN 2: COSTO DE OPORTUNIDAD**")
        st.metric("Tasa Caución (TEM)", f"{tem_caucion:.2f}%")
        st.metric("Diferencial Letra vs Caución", f"{diff_tasa:.2f}%")
        
        if diff_tasa > 0.35:
            st.success("VERDICTO: EFICIENCIA EN LETRAS")
        else:
            st.info("VERDICTO: EFICIENCIA EN CAUCIÓN")
        st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # AUDITORÍA DE LÓGICA (DESGLOSE PASO A PASO)
    # ─────────────────────────────────────────────
    st.divider()
    st.subheader("🕵️ Auditoría de Lógica (Verificación Manual)")

    with st.expander("Ver fórmulas y desgloses de este análisis"):
        st.markdown(f"""
        ### 1. El Dólar de Equilibrio (Ajuste por Riesgo)
        El sistema calcula cuánto "debería" valer el dólar según el miedo del mercado.
        *   **Fórmula:** `Dólar Mercado * (1 + (Riesgo País / 10.000))`
        *   **Tu Cálculo:** `{ccl_calculado:.2f} * (1 + {riesgo_pais/10000})` = **${ccl_teorico:.2f}**
        *   **Análisis:** El precio real (${ccl_calculado:.2f}) está un **{abs(press_ratio):.2f}%** por debajo del equilibrio.

        ### 2. El Arbitraje de Tasa (Normalización)
        *   **TEM Caución:** `({tasa_caucion}% / 365 * 30)` = **{tem_caucion:.2f}%**.
        *   **TEM Letra:** **{tasa_lecap:.2f}%**.
        *   **Spread:** **{diff_tasa:.2f}%**. 
        """)

    # ─────────────────────────────────────────────
    # ORDEN EJECUTIVA
    # ─────────────────────────────────────────────
    st.divider()
    if press_ratio < -4:
        msg = f"ORDEN: 80% RENTA VARIABLE (CEDEAR/BTC). El dólar de ${ccl_calculado:.2f} es barato para un riesgo de {riesgo_pais} bps."
        st.markdown(f'<div class="verdict-box" style="background-color:#C8E6C9; color:#1B5E20;">{msg}</div>', unsafe_allow_html=True)
    else:
        msg = "ORDEN: POSICIÓN NEUTRAL (50/50). Esperar confirmación en la Matrix de Señales."
        st.markdown(f'<div class="verdict-box" style="background-color:#E3F2FD; color:#0D47A1;">{msg}</div>', unsafe_allow_html=True)
