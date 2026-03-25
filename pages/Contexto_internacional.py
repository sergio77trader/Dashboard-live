import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(page_title="SLY v8.3: Zero Ambiguity", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .forensic-card { background-color: white; padding: 20px; border-radius: 15px; border-left: 8px solid #004a99; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .arbitrage-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border: 1px solid #004a99; color: #004a99; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_scalar_data():
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "AL30": "AL30.BA", "AL30D": "AL30D.BA"
    }
    data_results = {}
    
    for key, ticker in symbols.items():
        try:
            # Descarga individual
            df_temp = yf.download(ticker, period="7d", interval="1d", progress=False)
            if not df_temp.empty:
                # Forzamos la extracción del último valor como un número decimal puro (float)
                val = df_temp['Close'].ffill().iloc[-1]
                # Si por error devuelve una serie, tomamos el primer elemento
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                data_results[key] = float(val)
            else:
                data_results[key] = 0.0
        except:
            data_results[key] = 0.0
    
    return data_results

try:
    # --- EJECUCIÓN ---
    data = fetch_scalar_data()
    
    # 1. CÁLCULOS MATEMÁTICOS (Basados en escalares puros)
    ccl = (data["LOCAL"] / data["ADR"]) * 10 if data["ADR"] > 0 else 0.0
    mep = (data["AL30"] / data["AL30D"]) if data["AL30D"] > 0 else 0.0
    risk_proxy = 100.0 / data["AL30D"] if data["AL30D"] > 0 else 0.0
    
    # 2. MOTOR DE DECISIÓN (Lógica SLY)
    score = 0
    # Factores Externos
    if data["DXY"] > 100: score -= 20
    if data["BRL"] > 5.20: score -= 20
    # Factores Internos (Si bonos caen, dólar sube)
    if data["AL30D"] < 35: score -= 30
    
    if score <= -40:
        status, color, action = "ALERTA DE SISTEMA", "#d93025", "COMPRA DÓLAR / USDT - COBERTURA"
    elif score >= 20:
        status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS - OPORTUNIDAD"
    else:
        status, color, action = "POSICIÓN NEUTRAL", "#007bff", "SIN CAMBIOS OPERATIVOS"

    # --- UI: CABECERA ---
    st.markdown(f"""
        <div style="background-color: {color}; padding: 25px; border-radius: 15px; text-align: center; color: white;">
            <h1 style="margin:0;">{status}</h1>
            <h2 style="opacity:0.9; margin:0;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- UI: ARBITRAJE ---
    st.write("")
    col_arb1, col_arb2 = st.columns(2)
    with col_arb1:
        spread = ((ccl / mep) - 1) * 100 if mep > 0 else 0.0
        st.markdown(f"""
        <div class="arbitrage-box">
            ⚖️ SPREAD CCL vs MEP: {spread:.1f}%<br>
            RECOMENDACIÓN: {'Comprar MEP / USDT' if spread > 2 else 'Precios equilibrados'}
        </div>
        """, unsafe_allow_html=True)
    with col_arb2:
        st.markdown(f"""
        <div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">
            🛰️ RIESGO PAÍS PROXY: {risk_proxy:.2f}<br>
            ESTADO: {'🔴 PRESIÓN ALTA' if risk_proxy > 2.8 else '🟢 ESTABLE'}
        </div>
        """, unsafe_allow_html=True)

    # --- UI: MÉTRICAS ---
    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dólar CCL", f"${ccl:,.1f}")
    m1.metric("Dólar MEP", f"${mep:,.1f}")
    m2.metric("Oro (XAU)", f"${data['ORO']:,.0f}")
    m3.metric("DXY Index", f"{data['DXY']:.2f}")
    m4.metric("Dólar Brasil", f"{data['BRL']:.3f}")

    # --- UI: FORENSE ---
    st.markdown(f"""
    <div class="forensic-card">
        <h3>🔍 Análisis de Situación</h3>
        • <b>Dólar Global:</b> {'Presión Alta' if data['DXY']>100 else 'Normal'}<br>
        • <b>Brasil:</b> {'Devaluando' if data['BRL']>5.25 else 'Estable'}<br>
        • <b>Bonos Argentina:</b> {'Liquidación de Carteras' if data['AL30D']<35 else 'Sostenidos'}
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Fallo en el motor de cálculo: {e}")

st.info("SystemaTrader v8.3: Error de ambigüedad resuelto. El sistema ahora garantiza valores escalares para la toma de decisiones.")
