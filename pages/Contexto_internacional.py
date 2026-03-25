import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SLY: Macro Intelligence Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1c1e21; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; }
    .command-box { padding: 30px; border-radius: 15px; margin-bottom: 20px; text-align: center; }
    .detail-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #004a99; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_data():
    # Usamos tickers de alta liquidez
    symbols = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA"}
    df = yf.download(list(symbols.values()), period="5d", interval="1h", progress=False)['Close']
    return df.ffill().bfill(), symbols

df, symbols = fetch_data()

if df is not None:
    # --- CÁLCULOS MATEMÁTICOS CORREGIDOS ---
    adr_now = df[symbols["ADR"]].iloc[-1]
    local_now = df[symbols["LOCAL"]].iloc[-1]
    
    # FÓRMULA CORRECTA CCL: (Local / ADR) * Ratio (GGAL es 10)
    ccl = (local_now / adr_now) * 10 if adr_now > 0 else 0

    dxy_ch = ((df[symbols["DXY"]].iloc[-1] / df[symbols["DXY"]].iloc[-2]) - 1) * 100
    brl_ch = ((df[symbols["BRL"]].iloc[-1] / df[symbols["BRL"]].iloc[-2]) - 1) * 100
    oro_ch = ((df[symbols["ORO"]].iloc[-1] / df[symbols["ORO"]].iloc[-2]) - 1) * 100

    # --- DETECTOR DE FERIADOS / CIERRE ---
    # Si la data local no se movió en las últimas 4h pero la de afuera sí, es feriado.
    is_holiday = df[symbols["LOCAL"]].iloc[-1] == df[symbols["LOCAL"]].iloc[-4]

    # --- LÓGICA DE MANDO ---
    score = 0
    if dxy_ch > 0.2: score -= 30
    if brl_ch > 0.4: score -= 30
    if oro_ch > 0.1: score += 20
    
    if score <= -40:
        decision, color, msg = "🛡️ COBERTURA TOTAL", "#d93025", "ALERTA: El dólar global presiona al peso. Cúbrete."
    elif score >= 20:
        decision, color, msg = "🚲 CARRY TRADE POSIBLE", "#188038", "OK: El contexto global permite ganar tasa en pesos."
    else:
        decision, color, msg = "⏳ NEUTRAL", "#00aaff", "Mantén cautela. No hay desequilibrios masivos."

    # --- UI ---
    st.markdown(f"""
        <div class="command-box" style="background-color: {color}15; border: 2px solid {color};">
            <h1 style="color: {color}; margin: 0;">{decision}</h1>
            <h3 style="color: #3c4043;">{msg}</h3>
            {f'<p style="color:red;">⚠️ MERCADO LOCAL CERRADO O SIN DATA (FERIADO)</p>' if is_holiday else ''}
        </div>
        """, unsafe_allow_html=True)

    st.subheader("🔍 Por qué el bot dice esto:")
    c_a, c_b = st.columns(2)
    with c_a:
        st.markdown(f"""
        <div class="detail-card">
            <h4>🌍 Escenario Global</h4>
            • <b>Dólar Global (DXY):</b> {'📈 Fortaleciéndose' if dxy_ch > 0 else '📉 Debilitándose'}<br>
            • <b>Oro:</b> {'✨ Subiendo (Dólar global débil)' if oro_ch > 0 else '🔻 Bajando'}<br>
            • <b>Brasil:</b> {'⚠️ Devaluando' if brl_ch > 0.2 else '✅ Estable'}
        </div>
        """, unsafe_allow_html=True)
    with c_b:
        st.markdown(f"""
        <div class="detail-card" style="border-left-color: #f29900;">
            <h4>🇦🇷 Análisis del Peso</h4>
            • <b>Dólar CCL Calculado:</b> ${ccl:,.2f}<br>
            • <b>Presión Regional:</b> {'Alta' if brl_ch > 0.4 else 'Baja'}<br>
            • <b>Acción Galicia:</b> {'Estable' if not is_holiday else 'Sin cotización hoy'}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar CCL", f"${ccl:,.2f}")
    c2.metric("Oro (XAU)", f"${df[symbols['ORO']].iloc[-1]:.1f}", f"{oro_ch:+.2f}%")
    c3.metric("DXY Global", f"{df[symbols['DXY']].iloc[-1]:.2f}", f"{dxy_ch:+.2f}%", delta_color="inverse")
    c4.metric("Dólar Brasil", f"{df[symbols['BRL']].iloc[-1]:.3f}", f"{brl_ch:+.2f}%", delta_color="inverse")

st.button("🔄 Sincronizar con Londres")
