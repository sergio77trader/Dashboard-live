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
    # ─────────────────────────────────────────────
    # CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME
    # ─────────────────────────────────────────────
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
    # MOTOR DE DATOS EN VIVO (REDUNDANCIA DUAL)
    # ─────────────────────────────────────────────
    @st.cache_data(ttl=600)
    def fetch_live_ccl():
        try:
            # Intentamos con GGAL y AL30 para evitar el error NaN
            tickers = ["GGAL.BA", "GGAL", "AL30.BA", "AL30"]
            data = yf.download(tickers, period="1mo", interval="1d", progress=False)['Close']
            data = data.ffill().dropna()

            if not data.empty:
                # Prioridad 1: Ratio GGAL
                if "GGAL.BA" in data and "GGAL" in data:
                    ccl_ggal = (data["GGAL.BA"].iloc[-1] * 10) / data["GGAL"].iloc[-1]
                    if not np.isnan(ccl_ggal) and ccl_ggal > 0:
                        return float(ccl_ggal)
                
                # Prioridad 2: Ratio AL30
                if "AL30.BA" in data and "AL30" in data:
                    ccl_al30 = data["AL30.BA"].iloc[-1] / data["AL30"].iloc[-1]
                    if not np.isnan(ccl_al30) and ccl_al30 > 0:
                        return float(ccl_al30)
            
            return 1300.0 # Fallback si nada funciona
        except:
            return 1300.0

    # ─────────────────────────────────────────────
    # INTERFAZ Y CÁLCULOS
    # ─────────────────────────────────────────────
    now = datetime.datetime.now()
    st.title("🏛️ SLY | MONETARY PHYSICS ENGINE")
    st.write(f"**AUDITORÍA DE FLUJOS - FECHA PROCESAMIENTO:** {now.strftime('%d/%m/%Y %H:%M')}")

    live_ccl_val = fetch_live_ccl()

    with st.sidebar:
        st.header("⚙️ Variables de Mercado 2026")
        ccl_mkt = st.number_input("Dólar CCL Mercado ($):", value=live_ccl_val)
        riesgo_pais = st.number_input("Riesgo País (bps):", value=1200)
        
        st.divider()
        st.subheader("Tasas de Interés")
        tasa_caucion = st.number_input("Tasa Caución (TNA %):", value=38.0)
        tasa_lecap = st.number_input("Tasa Letra/Lefi (TEM %):", value=3.5)
        if st.button("🔒 Cerrar Sesión"):
            st.session_state["authenticated"] = False
            st.rerun()

    # LÓGICA MATEMÁTICA
    # 1. Dólar de Equilibrio
    ccl_teorico = ccl_mkt * (1 + riesgo_pais / 10000)
    press_ratio = (ccl_mkt / ccl_teorico - 1) * 100

    # 2. Arbitraje de Tasas
    tem_caucion = (tasa_caucion / 365) * 30
    diff_tasa = tasa_lecap - tem_caucion

    # ─────────────────────────────────────────────
    # VISUALIZACIÓN
    # ─────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("🟢 **DIMENSIÓN 1: EL PRECIO DEL DÓLAR**")
        st.metric("Brecha vs Dólar de Equilibrio", f"{press_ratio:.2f}%")
        
        if press_ratio < -5:
            st.success("VERDICTO: DÓLAR SUBVALUADO (BARATO)")
        elif press_ratio > 2:
            st.error("VERDICTO: DÓLAR SOBREVALUADO (CARO)")
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
    # AUDITORÍA DE LÓGICA (EXPLICACIÓN)
    # ─────────────────────────────────────────────
    st.divider()
    st.subheader("🕵️ Auditoría de Lógica (Verificación Manual)")

    with st.expander("Ver fórmulas y desgloses de este análisis"):
        st.markdown(f"""
        ### 1. El Dólar de Equilibrio (Física de Riesgo)
        El sistema entiende que a mayor riesgo país, más alto debería ser el dólar para compensar la fragilidad.
        *   **Fórmula:** `Dólar Mercado * (1 + (Riesgo País / 10.000))`
        *   **Cálculo actual:** `{ccl_mkt} * (1 + {riesgo_pais/10000})` = **${ccl_teorico:,.2f}**
        *   **Interpretación:** Si el precio actual (${ccl_mkt}) es menor al teórico, los CEDEARs tienen un "colchón" de seguridad.

        ### 2. El Arbitraje de Tasa (Eficiencia de Caja)
        Comparamos cuánto rinde "dejar la plata quieta" vs "invertirla en letras".
        *   **TEM Caución:** `({tasa_caucion}% / 365 * 30)` = **{tem_caucion:.2f}%**.
        *   **TEM Letra:** **{tasa_lecap:.2f}%**.
        *   **Diferencia:** **{diff_tasa:.2f}%**. 
        *   **Interpretación:** Si la diferencia es positiva (>0.4%), estás perdiendo dinero por no migrar de Caución a Letras.
        """)

    # ─────────────────────────────────────────────
    # ORDEN EJECUTIVA
    # ─────────────────────────────────────────────
    st.divider()
    st.subheader("🎯 Orden Ejecutiva del Sistema")

    if press_ratio < -5 and diff_tasa < 0.4:
        msg = "ACCIONAR: 80% RENTA VARIABLE (CEDEAR/BTC) / 20% CAUCIÓN. El dólar está barato respecto al riesgo."
        st.markdown(f'<div class="verdict-box" style="background-color:#C8E6C9; color:#1B5E20;">{msg}</div>', unsafe_allow_html=True)
    elif press_ratio > 0 and diff_tasa > 0.4:
        msg = "ACCIONAR: 20% RENTA VARIABLE / 80% LETRAS (LECAP). Capturar tasa real y proteger capital en pesos."
        st.markdown(f'<div class="verdict-box" style="background-color:#FFF9C4; color:#827717;">{msg}</div>', unsafe_allow_html=True)
    else:
        msg = "ACCIONAR: POSICIÓN NEUTRAL (50/50). No hay una ventaja clara en dólar o tasa. Esperar señales técnicas."
        st.markdown(f'<div class="verdict-box" style="background-color:#E3F2FD; color:#0D47A1;">{msg}</div>', unsafe_allow_html=True)
