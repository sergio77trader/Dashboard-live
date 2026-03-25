import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(page_title="SLY v8.1: Holiday Resilience", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .forensic-card { background-color: white; padding: 20px; border-radius: 15px; border-left: 8px solid #004a99; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .arbitrage-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border: 1px solid #004a99; color: #004a99; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_alpha_data():
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "SOJA": "ZS=F",
        "AL30": "AL30.BA", "AL30D": "AL30D.BA"
    }
    # Pedimos 60 días para asegurar que haya data histórica suficiente
    df = yf.download(list(symbols.values()), period="60d", interval="1d", progress=False)['Close']
    # Protocolo de limpieza profunda
    df = df.ffill().bfill()
    return df, symbols

try:
    df, symbols = fetch_alpha_data()
    
    # --- FUNCIÓN DE EXTRACCIÓN SEGURA (ANTI-NAN) ---
    def get_valid_last(key):
        series = df[symbols[key]].dropna()
        return series.iloc[-1] if not series.empty else 0

    # --- CÁLCULOS DE DÓLAR Y ARBITRAJE ---
    # 1. Dólar CCL (via GGAL)
    adr_val = get_valid_last("ADR")
    local_val = get_valid_last("LOCAL")
    ccl = (local_val / adr_val) * 10 if adr_val > 0 else 0
    
    # 2. Dólar MEP (via Bonos AL30)
    al30_p = get_valid_last("AL30")
    al30d_p = get_valid_last("AL30D")
    # Si los bonos fallan, el sistema no muestra nan, muestra 0 para alertar
    mep = al30_p / al30d_p if al30d_p > 0 else 0
    
    # 3. Riesgo País Proxy
    risk_proxy = 100 / al30d_p if al30d_p > 0 else 0
    
    # --- MOTOR DE DECISIÓN v8.1 ---
    score = 0
    points = []
    
    # Z-Score simplificado para evitar errores de std dev en feriados
    returns = df[symbols["DXY"]].pct_change().dropna()
    z_dxy = (returns.iloc[-1] - returns.mean()) / returns.std() if not returns.empty else 0

    # Lógica de Alerta
    if z_dxy > 1.2:
        score -= 40
        points.append(f"🔴 Dólar Global fuerte (Z:{z_dxy:.1f}) - Presión de subida.")
    
    if get_valid_last("BRL") > df[symbols["BRL"]].mean():
        score -= 20
        points.append("🔴 Brasil devaluado - Presión regional.")

    # --- DETERMINACIÓN DE ACCIÓN ---
    if score <= -40:
        status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLAR / USDT YA"
    elif score >= 20:
        status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS"
    else:
        status, color, action = "POSICIÓN NEUTRAL", "#007bff", "MANTÉN POSICIÓN ACTUAL"

    # --- UI: CABECERA ---
    st.markdown(f"""
        <div style="background-color: {color}; padding: 25px; border-radius: 15px; text-align: center; color: white;">
            <h1 style="margin:0;">{status}</h1>
            <h2 style="opacity:0.9; margin:0;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- UI: PANEL ALPHA (ARBITRAJE) ---
    st.write("")
    col_arb1, col_arb2 = st.columns(2)
    with col_arb1:
        spread = ((ccl / mep) - 1) * 100 if mep > 0 else 0
        st.markdown(f"""
        <div class="arbitrage-box">
            ⚖️ ARBITRAJE: El CCL es {spread:.1f}% más caro que el MEP.<br>
            RECOMENDACIÓN: {'Comprar MEP / USDT' if spread > 2 else 'Precios equilibrados'}
        </div>
        """, unsafe_allow_html=True)
    with col_arb2:
        st.markdown(f"""
        <div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">
            🛰️ RIESGO PAÍS PROXY: {risk_proxy:.2f} units<br>
            ESTADO: {'🔴 PRESIÓN ALTA' if risk_proxy > 2.5 else '🟢 ESTABLE'}
        </div>
        """, unsafe_allow_html=True)

    # --- MÉTRICAS ---
    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dólar CCL", f"${ccl:,.1f}")
    m1.metric("Dólar MEP", f"${mep:,.1f}")
    m2.metric("Oro (XAU)", f"${get_valid_last('ORO'):,.0f}")
    m3.metric("DXY Index", f"{get_valid_last('DXY'):.2f}")
    m4.metric("Dólar Brasil", f"{get_valid_last('BRL'):.3f}")

    # --- GRÁFICO ---
    st.subheader("📊 Gráfico de Convergencia (Últimos 60 Días)")
    def norm(s): return (s / s.iloc[0]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["ORO"]]), name="ORO", line=dict(color='#d4af37', width=4)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["DXY"]]), name="DXY", line=dict(color='#004a99')))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["AL30D"]]), name="BONO USD", line=dict(color='#d93025', dash='dot')))
    fig.update_layout(plot_bgcolor='white', height=450)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Fallo de conexión o feriado: {e}")

st.info("SystemaTrader: v8.1 activa. Usando 'Fallback' de datos históricos por feriado del 24 de Marzo.")
