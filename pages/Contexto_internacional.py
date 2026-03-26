import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="SLY v10.0: The Aggregator", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .command-box { padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .arbitrage-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border: 1px solid #004a99; color: #004a99; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS HÍBRIDO (YAHOO + DOLAR API) ---
@st.cache_data(ttl=300)
def fetch_unified_data():
    data = {
        "mep": 0.0, "ccl": 0.0, "blue": 0.0, "riesgo": 0.0,
        "oro": 0.0, "dxy": 0.0, "brl": 0.0,
        "history": {}
    }
    
    # A. OBTENER DATOS DE ARGENTINA (Fuente: DolarAPI - Redundante)
    try:
        # MEP
        res_mep = requests.get("https://dolarapi.com/v1/dolares/mep", timeout=5).json()
        data["mep"] = float(res_mep['compra'])
        # CCL
        res_ccl = requests.get("https://dolarapi.com/v1/dolares/contadoconliqui", timeout=5).json()
        data["ccl"] = float(res_ccl['compra'])
        # RIESGO PAÍS
        res_risk = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=5).json()
        data["riesgo"] = float(res_risk['valor'])
    except:
        st.warning("⚠️ Fuente local en mantenimiento. Usando estimaciones de respaldo...")

    # B. OBTENER DATOS GLOBALES (Fuente: Yahoo Finance)
    global_tickers = {"GLD": "GLD", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X"}
    try:
        df_global = yf.download(list(global_tickers.values()), period="30d", interval="1d", progress=False)['Close']
        df_global = df_global.ffill()
        
        data["oro"] = float(df_global["GLD"].iloc[-1]) * 10
        data["dxy"] = float(df_global["DX-Y.NYB"].iloc[-1])
        data["brl"] = float(df_global["USDBRL=X"].iloc[-1])
        data["history"] = df_global
    except Exception as e:
        st.error(f"Fallo en data global: {e}")

    return data

# --- 3. LÓGICA DE PROCESAMIENTO ---
try:
    st.title("🛡️ SLY Engine: Aggregator Terminal v10.0")
    
    d = fetch_unified_data()

    # --- 4. MOTOR DE DECISIÓN SLY ---
    score = 0
    # Factores Globales
    if d["dxy"] > 100: score -= 25
    if d["brl"] > 5.25: score -= 25
    # Factor Local (Riesgo País)
    if d["riesgo"] > 1500: score -= 30

    if score <= -40:
        status, color, action = "ALERTA CRÍTICA", "#d93025", "COMPRA DÓLAR / USDT - PROTECCIÓN"
    elif score >= 20:
        status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS - OPORTUNIDAD"
    else:
        status, color, action = "POSICIÓN NEUTRAL", "#007bff", "SIN CAMBIOS OPERATIVOS"

    # --- 5. RENDERIZADO ---
    st.markdown(f"""
        <div class="command-box" style="background-color: {color};">
            <h1 style="margin:0; color:white; border:none;">{status}</h1>
            <h2 style="margin:0; color:white; opacity:0.9; border:none;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        spread = ((d["ccl"] / d["mep"]) - 1) * 100 if d["mep"] > 0 else 0
        st.markdown(f"""<div class="arbitrage-box">⚖️ SPREAD CCL vs MEP: {spread:.1f}%<br>RECOMENDACIÓN: {'Comprar MEP / USDT' if spread > 2 else 'Precios equilibrados'}</div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">🛰️ RIESGO PAÍS REAL: {d['riesgo']:.0f} pts<br>ESTADO: {'🔴 ALTO' if d['riesgo'] > 1600 else '🟢 CONTROLADO'}</div>""", unsafe_allow_html=True)

    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dólar CCL", f"${d['ccl']:,.1f}")
    m1.metric("Dólar MEP", f"${d['mep']:,.1f}")
    m2.metric("Oro (XAU)", f"${d['oro']:,.0f}")
    m3.metric("DXY Index", f"{d['dxy']:.2f}")
    m4.metric("Dólar Brasil", f"{d['brl']:.3f}")

    # --- 6. GRÁFICOS ---
    st.subheader("📈 Tendencias Globales (Base 100)")
    if not d["history"].empty:
        fig = go.Figure()
        # Normalización
        def n(key): return (d["history"][key] / d["history"][key].iloc[0]) * 100
        
        fig.add_trace(go.Scatter(x=d["history"].index, y=n("GLD"), name="ORO", line=dict(color='#d4af37', width=3)))
        fig.add_trace(go.Scatter(x=d["history"].index, y=n("DX-Y.NYB"), name="DXY", line=dict(color='#004a99')))
        fig.add_trace(go.Scatter(x=d["history"].index, y=n("USDBRL=X"), name="BRASIL", line=dict(color='#188038')))
        
        fig.update_layout(plot_bgcolor='white', height=450, margin=dict(l=0,r=0,t=0,b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Fallo crítico en el Agregador: {e}")

if st.button('🔄 REFRESCAR SISTEMA'):
    st.cache_data.clear()
    st.rerun()
