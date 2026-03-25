import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE INTERFAZ PROFESIONAL ---
st.set_page_config(page_title="SYSTEMATRADER: Comando Macro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .stMetric { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .recommendation-box { padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .rec-title { font-size: 2.2em; font-weight: bold; margin-bottom: 5px; }
    .rec-detail { font-size: 1.2em; color: #444; }
    h2, h3 { color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_data_v5():
    # Diccionario Maestro de Activos
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "SOJA": "ZS=F"
    }
    df = yf.download(list(symbols.values()), period="5d", interval="1h", progress=False)['Close']
    return df.ffill().bfill(), symbols

try:
    df, symbols = get_data_v5()
    
    # --- CÁLCULOS QUANTS ---
    adr_now = df[symbols["ADR"]].iloc[-1]
    local_now = df[symbols["LOCAL"]].iloc[-1]
    ccl = (local_now / adr_now) * 10 if adr_now > 0 else 0
    
    dxy_ch = ((df[symbols["DXY"]].iloc[-1] / df[symbols["DXY"]].iloc[-2]) - 1) * 100
    brl_ch = ((df[symbols["BRL"]].iloc[-1] / df[symbols["BRL"]].iloc[-2]) - 1) * 100
    oro_ch = ((df[symbols["ORO"]].iloc[-1] / df[symbols["ORO"]].iloc[-2]) - 1) * 100
    soja_ch = ((df[symbols["SOJA"]].iloc[-1] / df[symbols["SOJA"]].iloc[-2]) - 1) * 100

    # --- MOTOR DE RECOMENDACIÓN (LÓGICA DE MANDO) ---
    score = 0
    if dxy_ch > 0.3: score -= 35 # El dólar global sube, peso baja
    if brl_ch > 0.5: score -= 30 # Brasil devalúa, presión en ARS
    if soja_ch < -1.0: score -= 20 # Menos dólares de la cosecha
    if oro_ch > 0.2: score += 25 # Oro sube, dólar global débil (bueno para ARS)

    if score <= -40:
        rec_text, rec_color, rec_msg = "🛡️ COMPRAR DÓLARES", "#d93025", "ESTADO DE COBERTURA: El contexto global asfixia al peso argentino. Protege tu capital en moneda dura."
    elif score >= 20:
        rec_text, rec_color, rec_msg = "🚲 HACER CARRY TRADE", "#188038", "ESTADO DE OPORTUNIDAD: El mundo está tranquilo. Vende dólares y gana tasa en pesos (Lecaps/Plazo Fijo)."
    else:
        rec_text, rec_color, rec_msg = "⏳ MANTENER / NEUTRAL", "#007bff", "ESTADO DE OBSERVACIÓN: No hay señales claras de desequilibrio. Mantén tus posiciones actuales."

    # --- UI: CENTRO DE COMANDO (RECOMENDACIÓN) ---
    st.markdown(f"""
        <div class="recommendation-box" style="background-color: {rec_color}15; border: 3px solid {rec_color};">
            <div class="rec-title" style="color: {rec_color};">{rec_text}</div>
            <div class="rec-detail">{rec_msg}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- MÉTRICAS DE TRADING ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Dólar CCL", f"${ccl:,.1f}")
    c2.metric("Oro (XAU)", f"${df[symbols['ORO']].iloc[-1]:.0f}", f"{oro_ch:+.2f}%")
    c3.metric("Global (DXY)", f"{df[symbols['DXY']].iloc[-1]:.2f}", f"{dxy_ch:+.2f}%", delta_color="inverse")
    c4.metric("Brasil (BRL)", f"{df[symbols['BRL']].iloc[-1]:.3f}", f"{brl_ch:+.2f}%", delta_color="inverse")
    c5.metric("Soja (ZS)", f"{df[symbols['SOJA']].iloc[-1]:.1f}", f"{soja_ch:+.2f}%")

    # --- GRÁFICO DE CONVERGENCIA ---
    st.subheader("📊 Gráfico de Presión Macro (Últimas 120 horas)")
    
    # Normalización para que todas las líneas empiecen en 100 y sean comparables
    def normalize(series): return (series / series.iloc[0]) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=normalize(df[symbols["ORO"]]), name="Oro (La Verdad)", line=dict(color='#FFD700', width=4)))
    fig.add_trace(go.Scatter(x=df.index, y=normalize(df[symbols["DXY"]]), name="Dólar Global (DXY)", line=dict(color='#1E90FF', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=normalize(df[symbols["BRL"]]), name="Dólar Brasil (BRL)", line=dict(color='#32CD32', width=2)))
    
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, margin=dict(l=10,r=10,t=10,b=10),
        xaxis=dict(showgrid=True, gridcolor='#eeeeee'),
        yaxis=dict(showgrid=True, gridcolor='#eeeeee'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(f"SystemaTrader: Hoy es feriado en Argentina (24 de Marzo). El precio de GGAL es el cierre del viernes, pero el Oro, el DXY y Brasil son tiempo real.")

except Exception as e:
    st.error(f"Error de conexión con la red de datos: {e}")

st.button("🔄 Sincronizar Mercados")
