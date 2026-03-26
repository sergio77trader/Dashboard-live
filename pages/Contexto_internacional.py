import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="SLY v11.0: Survivor Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .command-box { padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .status-msg { padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 0.9em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS CON REDUNDANCIA TRIPLE ---
@st.cache_data(ttl=300)
def fetch_survivor_data():
    data = {"mep": 0.0, "ccl": 0.0, "riesgo": 0.0, "oro": 0.0, "dxy": 0.0, "brl": 0.0, "source": "None"}
    
    # --- PASO A: DATOS GLOBALES (SIEMPRE DISPONIBLES) ---
    global_tkrs = {"GLD": "GLD", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA"}
    try:
        df_g = yf.download(list(global_tkrs.values()), period="30d", interval="1d", progress=False)['Close'].ffill()
        data["oro"] = float(df_g["GLD"].iloc[-1]) * 10
        data["dxy"] = float(df_g["DX-Y.NYB"].iloc[-1])
        data["brl"] = float(df_g["USDBRL=X"].iloc[-1])
    except: pass

    # --- PASO B: DATOS LOCALES (CAPA 1: API DEDICADA) ---
    try:
        res_mep = requests.get("https://dolarapi.com/v1/dolares/mep", timeout=3).json()
        data["mep"] = float(res_mep['compra'])
        res_ccl = requests.get("https://dolarapi.com/v1/dolares/contadoconliqui", timeout=3).json()
        data["ccl"] = float(res_ccl['compra'])
        data["source"] = "DolarAPI (Real-Time)"
    except:
        # --- PASO C: DATOS LOCALES (CAPA 2: CÁLCULO ADR) ---
        try:
            adr = float(df_g["GGAL"].iloc[-1])
            local = float(df_g["GGAL.BA"].iloc[-1])
            if adr > 0:
                data["ccl"] = (local / adr) * 10
                data["mep"] = data["ccl"] * 0.98 # Estimación por spread histórico
                data["source"] = "Cálculo ADR (Inferred)"
        except:
            data["source"] = "Error de Conexión Total"

    # --- PASO D: RIESGO PAÍS (FALLBACK SEGURO) ---
    try:
        res_r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=3).json()
        data["riesgo"] = float(res_r['valor'])
    except:
        data["riesgo"] = 1580.0 # Valor promedio de seguridad para que el score no dé cero

    return data, df_g

try:
    st.title("🛡️ SLY Engine: Survivor Terminal v11.0")
    
    d, history = fetch_survivor_data()

    # --- 3. MOTOR DE DECISIÓN ---
    score = 0
    if d["dxy"] > 100: score -= 25
    if d["brl"] > 5.25: score -= 25
    if d["riesgo"] > 1550: score -= 30

    if score <= -40:
        status, color, action = "ALERTA CRÍTICA", "#d93025", "ASEGURAR DÓLARES / USDT"
    elif score >= 20:
        status, color, action = "CARRY TRADE", "#188038", "MANTÉN PESOS (OPORTUNIDAD)"
    else:
        status, color, action = "NEUTRAL", "#007bff", "SIN CAMBIOS OPERATIVOS"

    # --- 4. RENDERIZADO ---
    st.markdown(f'<div class="status-msg" style="background-color:#fff3cd;">📡 Fuente de datos actual: <b>{d["source"]}</b></div>', unsafe_allow_html=True)

    st.markdown(f"""
        <div class="command-box" style="background-color: {color};">
            <h1 style="margin:0; color:white; border:none;">{status}</h1>
            <h2 style="margin:0; color:white; opacity:0.9; border:none;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar CCL", f"${d['ccl']:,.1f}")
    c1.metric("Dólar MEP", f"${d['mep']:,.1f}")
    c2.metric("Oro (XAU)", f"${d['oro']:,.0f}")
    c3.metric("DXY Index", f"{d['dxy']:.2f}")
    c4.metric("Dólar Brasil", f"{d['brl']:.3f}")

    # --- 5. GRÁFICO (RESTAURADO) ---
    st.subheader("📈 Convergencia Global (Base 100)")
    fig = go.Figure()
    def n(k): return (history[k] / history[k].iloc[0]) * 100
    
    fig.add_trace(go.Scatter(x=history.index, y=n("GLD"), name="ORO", line=dict(color='#d4af37', width=3)))
    fig.add_trace(go.Scatter(x=history.index, y=n("DX-Y.NYB"), name="DXY", line=dict(color='#004a99')))
    fig.add_trace(go.Scatter(x=history.index, y=n("USDBRL=X"), name="BRASIL", line=dict(color='#188038')))
    
    fig.update_layout(plot_bgcolor='white', height=400, margin=dict(l=0,r=0,t=0,b=0), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error en terminal: {e}")

if st.button('🔄 RECARGAR SISTEMA'):
    st.cache_data.clear()
    st.rerun()
