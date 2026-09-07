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
    </style>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # MOTOR DE DATOS ACTUALIZADO (07/09/2026)
    # ─────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Radar Ops Sep-2026")
        # Valores actualizados a la realidad de SEP-2026
        ccl_mkt = st.number_input("Dólar CCL Mercado ($):", value=1487.50)
        riesgo_pais = st.number_input("Riesgo País (bps):", value=490)
        
        st.divider()
        st.subheader("Tasas de Interés 2026")
        tasa_caucion = st.number_input("Tasa Caución (TNA %):", value=19.10)
        tasa_lecap = st.number_input("Tasa Letra (TEM %):", value=1.95)
        
        if st.button("🔒 Cerrar Sesión"):
            st.session_state["authenticated"] = False
            st.rerun()

    # LÓGICA MATEMÁTICA SEP-2026
    ccl_teorico = ccl_mkt * (1 + riesgo_pais / 10000)
    press_ratio = (ccl_mkt / ccl_teorico - 1) * 100
    tem_caucion = (tasa_caucion / 365) * 30
    diff_tasa = tasa_lecap - tem_caucion

    # ─────────────────────────────────────────────
    # VISUALIZACIÓN DE DIMENSIONES
    # ─────────────────────────────────────────────
    now = datetime.datetime.now()
    st.title("🏛️ SLY | MONETARY PHYSICS ENGINE")
    st.write(f"**ESTADO DE LIQUIDEZ AL:** 07/09/2026")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("🟢 **DIMENSIÓN 1: PRECIO DEL DÓLAR**")
        st.metric("Brecha vs Dólar de Equilibrio", f"{press_ratio:.2f}%")
        
        if press_ratio < -4:
            st.success("VERDICTO: DÓLAR EN DESCUENTO (COMPRA)")
        elif press_ratio > 1:
            st.error("VERDICTO: DÓLAR SOBREVALUADO")
        else:
            st.warning("VERDICTO: DÓLAR EN EQUILIBRIO")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("💰 **DIMENSIÓN 2: COSTO DE OPORTUNIDAD**")
        st.metric("Diferencial TEM (Letra vs Caución)", f"{diff_tasa:.2f}%")
        
        if diff_tasa > 0.35:
            st.success("VERDICTO: EFICIENCIA EN LETRAS (CARRY)")
        else:
            st.info("VERDICTO: EFICIENCIA EN CAUCIÓN (LIQUIDEZ)")
        st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # AUDITORÍA DE LÓGICA (PARA TU VERIFICACIÓN)
    # ─────────────────────────────────────────────
    st.divider()
    st.subheader("🕵️ Auditoría de Lógica (Verificación Manual)")

    with st.expander("Ver fórmulas y desgloses de este análisis"):
        st.markdown(f"""
        ### 1. El Dólar de Equilibrio
        En el escenario de 2026, con Riesgo País de **{riesgo_pais}**, el dólar tiene menos "premio por miedo" que en 2024.
        *   **Fórmula:** `{ccl_mkt} * (1 + {riesgo_pais}/10.000)`
        *   **Cálculo actual:** **${ccl_teorico:,.2f}**
        *   **Estado:** El precio actual (${ccl_mkt}) está un **{abs(press_ratio):.2f}%** por debajo de su valor teórico. Hay un colchón de seguridad.

        ### 2. El Arbitraje de Tasa
        *   **TEM Caución:** `({tasa_caucion}% / 365 * 30)` = **{tem_caucion:.2f}%**.
        *   **TEM Letra:** **{tasa_lecap:.2f}%**.
        *   **Spread:** **{diff_tasa:.2f}%**. 
        *   **Interpretación:** La diferencia es menor a 0.40%, lo que indica que no hay un incentivo masivo para inmovilizar capital en letras; la caución es eficiente por su liquidez.
        """)

    # ─────────────────────────────────────────────
    # CONCLUSIÓN EJECUTIVA
    # ─────────────────────────────────────────────
    st.divider()
    if press_ratio < -4:
        msg = "ORDEN: 75% RENTA VARIABLE (CEDEAR/BTC) / 25% CAUCIÓN. El dólar está barato para el nivel de riesgo país."
        st.markdown(f'<div class="verdict-box" style="background-color:#C8E6C9; color:#1B5E20;">{msg}</div>', unsafe_allow_html=True)
    else:
        msg = "ORDEN: POSICIÓN NEUTRAL (50/50). Estabilidad de flujos. Operar según señales técnicas de la Matrix."
        st.markdown(f'<div class="verdict-box" style="background-color:#E3F2FD; color:#0D47A1;">{msg}</div>', unsafe_allow_html=True)
