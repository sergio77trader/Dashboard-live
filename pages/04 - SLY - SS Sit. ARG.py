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
    st.set_page_config(layout="wide", page_title="SLY | MONETARY ENGINE")

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
        .status-tag { padding: 5px 10px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # MOTOR DE CAPTURA DE DATOS (ESTRICTO)
    # ─────────────────────────────────────────────
    def safe_get_price(ticker):
        """Intenta obtener el precio, si falla devuelve 0.0 para validación posterior"""
        try:
            df = yf.download(ticker, period="5d", progress=False)
            if not df.empty:
                val = df['Close'].iloc[-1]
                if isinstance(val, pd.Series): val = val.iloc[0]
                return float(val)
        except:
            pass
        return 0.0

    # ─────────────────────────────────────────────
    # INTERFAZ Y ENTRADA DE DATOS
    # ─────────────────────────────────────────────
    st.title("🏛️ SLY | MONETARY PHYSICS ENGINE")
    
    with st.sidebar:
        st.header("⚙️ Entradas de Mercado")
        
        # Intentamos obtener data en vivo
        with st.spinner("Sincronizando con Wall Street..."):
            live_local = safe_get_price("GGAL.BA")
            live_adr = safe_get_price("GGAL")
        
        # VALIDACIÓN: Si la data es 0.0 o NaN, usamos tus últimos datos conocidos como default
        default_local = live_local if (live_local > 0 and not np.isnan(live_local)) else 6930.0
        default_adr = live_adr if (live_adr > 0 and not np.isnan(live_adr)) else 44.36
        
        # Etiquetas de estado
        if live_local > 0 and live_adr > 0:
            st.markdown('<span class="status-tag" style="background-color:#C8E6C9; color:#1B5E20;">🟢 CONEXIÓN EN VIVO</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-tag" style="background-color:#FFCDD2; color:#B71C1C;">🔴 MODO MANUAL (API BLOCKED)</span>', unsafe_allow_html=True)

        # INPUTS (Si la API falla, el usuario tiene el control total)
        local_in = st.number_input("Precio GGAL Local ($):", value=default_local, step=1.0)
        adr_in = st.number_input("Precio GGAL ADR (USD):", value=default_adr, step=0.01)
        riesgo_pais = st.number_input("Riesgo País (bps):", value=490)
        
        st.divider()
        st.subheader("Tasas de Interés")
        tasa_caucion = st.number_input("Tasa Caución (TNA %):", value=19.10)
        tasa_lecap = st.number_input("Tasa Letra (TEM %):", value=1.95)
        
        if st.button("🔒 Cerrar Sesión"):
            st.session_state["authenticated"] = False
            st.rerun()

    # ─────────────────────────────────────────────
    # LÓGICA DE FÍSICA MONETARIA (PROHIBIDO EL NAN)
    # ─────────────────────────────────────────────
    # Forzamos que los valores sean floats válidos
    local_val = float(local_in) if local_in > 0 else 6930.0
    adr_val = float(adr_in) if adr_in > 0 else 44.36
    
    # 1. Cálculo de Dólar Implícito
    ccl_calculado = (local_val * 10) / adr_val
    
    # 2. Dólar de Equilibrio (Ajustado por Riesgo)
    ccl_teorico = ccl_calculado * (1 + (riesgo_pais / 10000))
    press_ratio = (ccl_calculado / ccl_teorico - 1) * 100

    # 3. Arbitraje de Tasas
    tem_caucion = (tasa_caucion / 365) * 30
    diff_tasa = tasa_lecap - tem_caucion

    # ─────────────────────────────────────────────
    # VISUALIZACIÓN DE DIMENSIONES
    # ─────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.write("🟢 **DIMENSIÓN 1: PRECIO DEL DÓLAR**")
        st.metric("Dólar CCL Calculado", f"${ccl_calculado:,.2f}")
        st.metric("Brecha vs Equilibrio", f"{press_ratio:.2f}%")
        
        if press_ratio < -4:
            st.success("VERDICTO: DÓLAR EN DESCUENTO (BARATO)")
        elif press_ratio > 1:
            st.error("VERDICTO: DÓLAR SOBREVALUADO")
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
    # AUDITORÍA DE LÓGICA (DESGLOSE)
    # ─────────────────────────────────────────────
    st.divider()
    st.subheader("🕵️ Auditoría de Lógica (Verificación Manual)")
    with st.expander("Ver fórmulas del sistema"):
        st.markdown(f"""
        1. **Dólar Implícito:** `({local_val} * 10) / {adr_val}` = **${ccl_calculado:,.2f}**
        2. **Dólar de Equilibrio:** `${ccl_calculado:,.2f} * (1 + {riesgo_pais}/10.000)` = **${ccl_teorico:,.2f}**
        3. **Rendimiento Mensual:** `{tasa_caucion}% / 365 * 30` = **{tem_caucion:.2f}%**
        """)

    # ─────────────────────────────────────────────
    # ORDEN EJECUTIVA
    # ─────────────────────────────────────────────
    st.divider()
    if press_ratio < -4:
        msg = f"ORDEN: 80% RENTA VARIABLE (CEDEAR/BTC). El dólar está barato para un riesgo de {riesgo_pais} bps."
        st.markdown(f'<div class="verdict-box" style="background-color:#C8E6C9; color:#1B5E20;">{msg}</div>', unsafe_allow_html=True)
    elif press_ratio > 0 and diff_tasa > 0.4:
        msg = "ORDEN: 20% RENTA VARIABLE / 80% LETRAS (LECAP). Capturar tasa real y proteger capital."
        st.markdown(f'<div class="verdict-box" style="background-color:#FFF9C4; color:#827717;">{msg}</div>', unsafe_allow_html=True)
    else:
        msg = "ORDEN: POSICIÓN NEUTRAL (50/50). Esperar señales claras en la Matrix Técnica."
        st.markdown(f'<div class="verdict-box" style="background-color:#E3F2FD; color:#0D47A1;">{msg}</div>', unsafe_allow_html=True)
