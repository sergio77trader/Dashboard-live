import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE LA ESCUELA ---
st.set_page_config(page_title="SLY v14.0: Sweet Arbitrage", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .command-box { padding: 30px; border-radius: 20px; text-align: center; color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .school-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 10px solid #2196f3; margin-top: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .mentor-note { background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; color: #856404; font-size: 1em; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_institutional_data():
    tkrs = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA", "UST10Y": "^TNX"}
    df = yf.download(list(tkrs.values()), period="60d", interval="1d", progress=False)['Close'].ffill()
    return df, tkrs

try:
    st.title("🛡️ SLY Engine: Terminal v14.0 - Monitor de Dulces")
    df, tkrs = fetch_institutional_data()
    
    # --- CÁLCULOS QUANTS ---
    ccl = (df["GGAL.BA"].iloc[-1] / df["GGAL"].iloc[-1]) * 10
    tasa_usa = df["^TNX"].iloc[-1]
    
    # OBTENER RIESGO PAÍS Y TASA AR (DolarAPI / ArgentinaDatos)
    res_r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=3).json()
    riesgo = float(res_r['valor'])
    
    # Simulamos la Tasa de Política Monetaria actual (Sweets)
    # En producción, esto se conecta a la API del BCRA para Lecaps/Plazo Fijo
    tasa_ar_mensual = 3.5  # Premio del Director: 3.5% mensual (ajustable)
    
    dolar_respaldo = ccl * (1 + (riesgo / 10000))
    brecha_respaldo = ((dolar_respaldo / ccl) - 1) * 100

    # --- MOTOR DE DECISIÓN v14.0 ---
    score = 0
    if tasa_usa > 4.4: score -= 30
    if brecha_respaldo > 5: score -= 20
    if riesgo < 700: score += 20 # Si hay confianza, sumamos puntos para el Carry

    if score <= -40: status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES YA"
    elif score >= 25: status, color, action = "CARRY TRADE", "#188038", "GANAR INTERESES EN PESOS"
    else: status, color, action = "NEUTRAL", "#007bff", "QUÉDATE QUIETO / ESPERA"

    # --- UI: CARTEL DE MANDO ---
    st.markdown(f"""<div class="command-box" style="background-color: {color};"><h1>{status}</h1><h2>{action}</h2></div>""", unsafe_allow_html=True)

    # --- LA EXPLICACIÓN DEL NIÑO (EL PREMIO) ---
    st.subheader("🍭 El Monitor de Dulces (Tasa vs Riesgo)")
    col_sweets, col_logic = st.columns([1, 2])
    
    with col_sweets:
        st.write("### El Premio Actual")
        st.metric("Tasa Mensual (Dulces)", f"{tasa_ar_mensual}%", help="Este es el alfajor que te da el Director por mes.")
        st.metric("Riesgo de Derretimiento", f"{brecha_respaldo:.1f}%", delta=f"{brecha_respaldo:.1f}%", delta_color="inverse", help="Si el dólar salta este %, te quedas sin alfajor y sin figuritas.")

    with col_logic:
        st.markdown(f"""<div class="school-card">
        <span style="font-size:1.5em; font-weight:bold;">🏫 ¿Vale la pena el alfajor?</span><br>
        <p style="color:#444;">El Director te ofrece un <b>{tasa_ar_mensual}%</b> de dulces por mes. Pero el bot detecta que la puerta de salida está a un <b>{brecha_respaldo:.1f}%</b> de distancia (Dólar de Respaldo).<br><br>
        <b>Veredicto:</b> {'❌ NO. El peligro de que el dólar salte es mayor que el premio.' if brecha_respaldo > tasa_ar_mensual else '✅ SÍ. Por ahora el alfajor es más grande que el miedo.'}</p>
        </div>""", unsafe_allow_html=True)

    # --- PANEL DE AUDITORÍA ---
    st.write("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""<div class="school-card" style="border-left-color: #ff9800;">
        <b>🇦🇷 Nuestras Figuritas:</b> El Dólar real de ${ccl:.0f} es menor al de respaldo (${dolar_respaldo:.0f}).
        Estamos viviendo de la <b>confianza</b> (Riesgo {riesgo:.0f} pts). Si los niños se asustan, el alfajor no te salva.</div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="school-card" style="border-left-color: #f44336;">
        <b>🇺🇸 El Imán de afuera:</b> La tasa de {tasa_usa:.2f}% sigue encendida. No es una emergencia, pero el imán está trabajando 24/7 para llevarse el Oro de la caja.</div>""", unsafe_allow_html=True)

    # --- GRÁFICO DE CONVERGENCIA ---
    st.subheader("📈 ¿Hacia dónde corre el Oro? (Base 100)")
    fig = go.Figure()
    def n(k): return (df[k] / df[k].iloc[0]) * 100
    fig.add_trace(go.Scatter(x=df.index, y=n("GC=F"), name="ORO", line=dict(color='#d4af37', width=3)))
    fig.add_trace(go.Scatter(x=df.index, y=n("DX-Y.NYB"), name="DXY", line=dict(color='#004a99')))
    fig.add_trace(go.Scatter(x=df.index, y=n("^TNX"), name="IMÁN EEUU", line=dict(color='#f44336', dash='dot')))
    fig.update_layout(plot_bgcolor='white', height=450, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Sincronizando el patio de juegos... {e}")

st.button("🔄 RECALCULAR PREMIO")
