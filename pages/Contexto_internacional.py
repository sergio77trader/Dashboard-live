import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(page_title="SLY v8.0: Alpha Leak Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .forensic-card { background-color: white; padding: 20px; border-radius: 15px; border-left: 8px solid #004a99; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .arbitrage-box { background-color: #fff3cd; padding: 15px; border-radius: 10px; border: 1px solid #ffeeba; color: #856404; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_alpha_data():
    # Tickers: Oro, DXY, Brasil, Galicia ADR, Galicia Local, Soja, Bono Pesos, Bono Dólares
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "SOJA": "ZS=F",
        "AL30": "AL30.BA", "AL30D": "AL30D.BA"
    }
    df = yf.download(list(symbols.values()), period="60d", interval="1d", progress=False)['Close']
    return df.ffill().bfill(), symbols

try:
    df, symbols = fetch_alpha_data()
    
    # --- MOTOR DE CÁLCULO ESTADÍSTICO (Z-SCORE) ---
    def get_z_score(key):
        returns = df[symbols[key]].pct_change().dropna()
        last_return = returns.iloc[-1]
        return (last_return - returns.mean()) / returns.std()

    # --- CÁLCULOS DE DÓLAR Y ARBITRAJE ---
    # 1. Dólar CCL (via GGAL)
    ccl = (df[symbols["LOCAL"]].iloc[-1] / df[symbols["ADR"]].iloc[-1]) * 10
    
    # 2. Dólar MEP (via Bonos AL30)
    # Si AL30D no tiene data hoy, usamos el último ratio conocido
    mep = df[symbols["AL30"]].iloc[-1] / df[symbols["AL30D"]].iloc[-1]
    
    # 3. Riesgo País Proxy (Inverso del precio del bono en USD)
    risk_proxy = 100 / df[symbols["AL30D"]].iloc[-1]
    
    # --- MOTOR DE DECISIÓN v8.0 ---
    score = 0
    points = []
    
    z_dxy = get_z_score("DXY")
    z_brl = get_z_score("BRL")
    z_oro = get_z_score("ORO")

    # Evaluación de Amenazas Globales
    if z_dxy > 1.5:
        score -= 40
        points.append(f"🔴 ANOMALÍA DXY: El dólar global sube con fuerza inusual (Z:{z_dxy:.1f})")
    elif z_dxy < -1:
        score += 15
        points.append("🟢 DXY en caída: Presión externa liberada.")

    # Evaluación de Brasil (Efecto Espejo)
    if z_brl > 1.5:
        score -= 30
        points.append(f"🔴 SHOCK BRASIL: Devaluación violenta en el vecino (Z:{z_brl:.1f})")

    # Evaluación de Refugio
    if z_oro > 1:
        score += 20
        points.append("✨ ORO ACTIVADO: El mundo huye del dólar papel.")

    # Evaluación de Riesgo Local (Bonos)
    if df[symbols["AL30D"]].iloc[-1] < df[symbols["AL30D"]].iloc[-5]:
        score -= 25
        points.append("🔻 DERRUMBE DE BONOS: Los inversores salen de Argentina.")

    # --- DETERMINACIÓN DE ACCIÓN ---
    if score <= -40:
        status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLAR / USDT YA"
    elif score >= 20:
        status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS (TASAS ALTAS)"
    else:
        status, color, action = "POSICIÓN NEUTRAL", "#007bff", "MANTÉN POSICIÓN ACTUAL"

    # --- UI: CABECERA DE MANDO ---
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
        spread = ((ccl / mep) - 1) * 100
        st.markdown(f"""
        <div class="arbitrage-box">
            ⚖️ ARBITRAJE: El CCL es {spread:.1f}% más caro que el MEP.<br>
            RECOMENDACIÓN: {'Comprar MEP (Está barato)' if spread > 2 else 'Precios equilibrados'}
        </div>
        """, unsafe_allow_html=True)
    with col_arb2:
        st.markdown(f"""
        <div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">
            🛰️ RIESGO PAÍS PROXY: {risk_proxy:.2f} units<br>
            TENDENCIA: {'🔴 EMPEORANDO' if risk_proxy > 2.5 else '🟢 MEJORANDO'}
        </div>
        """, unsafe_allow_html=True)

    # --- UI: FORENSE DETALLADO ---
    st.markdown(f"""
    <div class="forensic-card">
        <h3>🔍 Forense de Inteligencia (Score: {score})</h3>
    """, unsafe_allow_html=True)
    for p in points:
        st.write(p)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- MÉTRICAS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar CCL (GGAL)", f"${ccl:,.1f}")
    c1.metric("Dólar MEP (AL30)", f"${mep:,.1f}")
    c2.metric("Oro (Truth)", f"${df[symbols['ORO']].iloc[-1]:.0f}", f"{z_oro:.1f}σ")
    c3.metric("DXY (USA)", f"{df[symbols['DXY']].iloc[-1]:.2f}", f"{z_dxy:.1f}σ", delta_color="inverse")
    c4.metric("Brasil (BRL)", f"{df[symbols['BRL']].iloc[-1]:.3f}", f"{z_brl:.1f}σ", delta_color="inverse")

    # --- GRÁFICO ---
    st.subheader("📊 Gráfico de Convergencia Estadística (Normalizado)")
    def norm(s): return (s / s.iloc[0]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["ORO"]]), name="ORO", line=dict(color='#d4af37', width=4)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["DXY"]]), name="DXY", line=dict(color='#004a99', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["AL30D"]]), name="BONO USD (Confianza)", line=dict(color='#d93025', width=2, dash='dot')))
    fig.update_layout(plot_bgcolor='white', height=500)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Esperando apertura de mercados... (Error: {e})")

st.info("SystemaTrader: Hoy es feriado en Argentina. El precio de los bonos y la local son del viernes. El resto es TIEMPO REAL.")
