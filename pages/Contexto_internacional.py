import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="SLY v9.0: Final Robust Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .command-box { padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .arbitrage-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border: 1px solid #004a99; color: #004a99; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS (RECOLECCIÓN INDIVIDUAL) ---
@st.cache_data(ttl=600)
def fetch_robust_data():
    symbols = {
        "GLD": "GLD", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X",
        "ADR": "GGAL", "LOCAL": "GGAL.BA", 
        "AL30": "AL30.BA", "AL30D": "AL30D.BA"
    }
    data_dict = {}
    history_dict = {}
    
    for key, ticker in symbols.items():
        try:
            # Pedimos 120 días para asegurar que los bonos aparezcan sí o sí
            df = yf.download(ticker, period="120d", interval="1d", progress=False)['Close']
            if not df.empty:
                df = df.ffill().dropna()
                data_dict[key] = float(df.iloc[-1])
                history_dict[key] = df
            else:
                data_dict[key] = 0.0
        except:
            data_dict[key] = 0.0
            
    return data_dict, history_dict, symbols

# --- 3. LÓGICA DE PROCESAMIENTO ---
try:
    st.title("🛡️ SLY Engine: Macro Truth Monitor v9.0")
    
    val, hist, syms = fetch_robust_data()

    # Cálculos con validación para evitar división por cero o NaNs
    ccl = (val["LOCAL"] / val["ADR"]) * 10 if val["ADR"] > 0 else 0.0
    mep = (val["AL30"] / val["AL30D"]) if val["AL30D"] > 0 else 0.0
    risk = 100 / val["AL30D"] if val["AL30D"] > 3 else 0.0

    # --- 4. MOTOR DE DECISIÓN SLY ---
    score = 0
    if val["DXY"] > 100: score -= 25
    if val["BRL"] > 5.25: score -= 25
    if val["AL30D"] > 0 and val["AL30D"] < 38: score -= 30

    if score <= -40:
        status, color, action = "ALERTA CRÍTICA", "#d93025", "COMPRA DÓLAR / USDT - PROTECCIÓN"
    elif score >= 20:
        status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS - OPORTUNIDAD"
    else:
        status, color, action = "POSICIÓN NEUTRAL", "#007bff", "MANTÉN TUS POSICIONES"

    # --- 5. RENDERIZADO ---
    st.markdown(f"""
        <div class="command-box" style="background-color: {color};">
            <h1 style="margin:0; color:white; border:none;">{status}</h1>
            <h2 style="margin:0; color:white; opacity:0.9; border:none;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        spread = ((ccl / mep) - 1) * 100 if mep > 0 else 0.0
        msg = f"⚖️ SPREAD CCL vs MEP: {spread:.1f}%" if mep > 0 else "⚖️ SPREAD: Sin datos de Bonos"
        st.markdown(f"""<div class="arbitrage-box">{msg}</div>""", unsafe_allow_html=True)
    with col_b:
        risk_txt = f"{risk:.2f}" if risk > 0 else "N/A"
        st.markdown(f"""<div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">🛰️ RIESGO PAÍS PROXY: {risk_txt}</div>""", unsafe_allow_html=True)

    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dólar CCL", f"${ccl:,.1f}")
    m1.metric("Dólar MEP", f"${mep:,.1f}" if mep > 0 else "Cerrado")
    m2.metric("Oro (XAU)", f"${val['GLD']*10:,.0f}")
    m3.metric("DXY Index", f"{val['DXY']:.2f}")
    m4.metric("Dólar Brasil", f"{val['BRL']:.3f}")

    # --- 6. GRÁFICO RESILIENTE ---
    st.subheader("📈 Tendencias (Base 100)")
    fig = go.Figure()
    
    # Solo graficamos activos con data para evitar crashes
    graph_assets = [("GLD", "#d4af37", "ORO"), ("DXY", "#004a99", "DXY"), ("AL30D", "#d93025", "BONO USD")]
    
    for key, color_hex, name in graph_assets:
        if key in hist and not hist[key].empty:
            norm_series = (hist[key] / hist[key].dropna().iloc[0]) * 100
            fig.add_trace(go.Scatter(x=norm_series.index, y=norm_series, name=name, line=dict(color=color_hex)))

    fig.update_layout(plot_bgcolor='white', height=450, margin=dict(l=0,r=0,t=0,b=0), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error técnico: {e}")

if st.button('🔄 REFRESCAR TERMINAL'):
    st.cache_data.clear()
    st.rerun()
