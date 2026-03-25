import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN INSTITUCIONAL ---
st.set_page_config(page_title="SYSTEMATRADER: Centro de Mandos", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .command-box { padding: 20px; border-radius: 10px; margin-bottom: 25px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_data():
    symbols = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA"}
    df = yf.download(list(symbols.values()), period="5d", interval="15m", progress=False)['Close']
    return df, symbols

try:
    df, symbols = fetch_data()
    
    # --- CÁLCULOS CRÍTICOS ---
    ccl = (df[symbols["ADR"]].iloc[-1] * 10) / df[symbols["LOCAL"]].iloc[-1]
    oro_ch = ((df[symbols["ORO"]].iloc[-1] / df[symbols["ORO"]].iloc[-2]) - 1) * 100
    dxy_ch = ((df[symbols["DXY"]].iloc[-1] / df[symbols["DXY"]].iloc[-2]) - 1) * 100
    brl_ch = ((df[symbols["BRL"]].iloc[-1] / df[symbols["BRL"]].iloc[-2]) - 1) * 100
    adr_ch = ((df[symbols["ADR"]].iloc[-1] / df[symbols["ADR"]].iloc[-2]) - 1) * 100

    # --- LÓGICA DE MANDO (EL "QUÉ HACER") ---
    # Definimos la recomendación exacta
    decision = ""
    color = ""
    detalles = ""

    if dxy_ch < 0 and oro_ch > 0.1 and brl_ch < 0.2 and adr_ch > -0.5:
        decision = "🚲 ESTADO: CARRY TRADE ACTIVO"
        color = "#00ff00" # Verde
        detalles = "El mundo está tranquilo y el Oro valida debilidad del dólar. Quédate en pesos y gana tasa (Lecaps/Plazo Fijo)."
    
    elif dxy_ch > 0.4 or brl_ch > 0.6:
        decision = "🛡️ ESTADO: COBERTURA TOTAL"
        color = "#ff4b4b" # Rojo
        detalles = "Alerta de succión de dólares global o devaluación en Brasil. SAL DE PESOS. Compra Dólar MEP/CCL o Cripto inmediatamente."
    
    elif adr_ch < -2.0:
        decision = "🚨 ESTADO: FUGA DE CAPITALES"
        color = "#ffaa00" # Naranja
        detalles = "Los fondos están vendiendo Argentina en NY. El dólar va a subir por presión de salida. No te quedes en pesos."
    
    else:
        decision = "⏳ ESTADO: NEUTRAL / OBSERVACIÓN"
        color = "#00aaff" # Azul
        detalles = "No hay señales claras de desequilibrio. Mantén tus posiciones actuales. No es momento de grandes cambios."

    # --- UI: CENTRO DE MANDOS ---
    st.markdown(f"""
        <div class="command-box" style="background-color: {color}22; border: 2px solid {color};">
            <h1 style="color: {color}; margin: 0;">{decision}</h1>
            <p style="color: white; font-size: 1.2em; margin-top: 10px;">{detalles}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- MÉTRICAS ---
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Dólar CCL", f"${ccl:.2f}")
    with col2: st.metric("Oro (XAU)", f"${df[symbols['ORO']].iloc[-1]:.1f}", f"{oro_ch:+.2f}%")
    with col3: st.metric("Dólar Global", f"{df[symbols['DXY']].iloc[-1]:.2f}", f"{dxy_ch:+.2f}%", delta_color="inverse")
    with col4: st.metric("Dólar Brasil", f"{df[symbols['BRL']].iloc[-1]:.4f}", f"{brl_ch:+.2f}%", delta_color="inverse")

    # --- GRÁFICO ---
    st.subheader("Radar de Inteligencia (Vigilancia 24/7)")
    def norm(col): return (df[col] / df[col].iloc[0]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["ORO"]), name="ORO", line=dict(color='gold', width=3)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["DXY"]), name="DXY (EE.UU)", line=dict(color='cyan')))
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["BRL"]), name="REAL (Brasil)", line=dict(color='lime')))
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["ADR"]), name="GGAL (NY)", line=dict(color='white', dash='dot')))
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("Mercados cerrados o sincronizando data...")
