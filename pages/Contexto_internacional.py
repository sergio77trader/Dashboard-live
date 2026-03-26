import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SLY v12.1: Mentor Edition", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .command-box { padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .logic-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 10px solid #004a99; margin-top: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .mentor-note { background-color: #e7f3ff; padding: 15px; border-radius: 8px; border-left: 5px solid #2196f3; font-size: 0.95em; color: #1e4976; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_institutional_data():
    tkrs = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA", "UST10Y": "^TNX"}
    df = yf.download(list(tkrs.values()), period="30d", interval="1d", progress=False)['Close'].ffill()
    return df, tkrs

try:
    st.title("🛡️ SLY Engine: Intelligence Terminal v12.1")
    df, tkrs = fetch_institutional_data()
    
    # --- CÁLCULOS QUANTS ---
    ccl = (df["GGAL.BA"].iloc[-1] / df["GGAL"].iloc[-1]) * 10
    tasa_usa = df["^TNX"].iloc[-1]
    
    # OBTENER RIESGO PAÍS REAL
    res_r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=3).json()
    riesgo = float(res_r['valor'])
    dolar_teorico = ccl * (1 + (riesgo / 10000))

    # --- MOTOR DE DECISIÓN ---
    score = 0
    if tasa_usa > 4.4: score -= 30
    if dolar_teorico > ccl * 1.05: score -= 20
    if riesgo > 1200: score -= 20

    if score <= -40: status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES / USDT YA"
    elif score >= 20: status, color, action = "CARRY TRADE", "#188038", "GANAR TASA EN PESOS"
    else: status, color, action = "NEUTRAL", "#007bff", "SIN CAMBIOS OPERATIVOS"

    # --- UI: RENDERIZADO ---
    st.markdown(f"""<div class="command-box" style="background-color: {color};"><h1>{status}</h1><h2>{action}</h2></div>""", unsafe_allow_html=True)

    # --- PANEL DE AUDITORÍA CON EXPLICACIÓN ---
    st.subheader("🔍 ¿Por qué tomamos esta decisión?")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown(f"""<div class="logic-card"><h4>🇦🇷 Monitor de Emisión y Respaldo</h4>
        • <b>Dólar Real:</b> ${ccl:.1f}<br>
        • <b>Dólar de Respaldo:</b> ${dolar_teorico:.1f}<br>
        • <b>Riesgo País:</b> {riesgo:.0f} pts</div>""", unsafe_allow_html=True)
        
        # EXPLICACIÓN DINÁMICA NIÑO - ARGENTINA
        if dolar_teorico > ccl:
            st.markdown("""<div class="mentor-note"><b>🏫 Lógica de la Escuela:</b> El Dólar está "barato". El Director está fabricando figuritas (Pesos) más rápido de lo que guarda Oro en la caja fuerte. <b>Peligro para el Carry Trade.</b></div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="mentor-note"><b>🏫 Lógica de la Escuela:</b> La caja fuerte está bien. Hay suficientes Cartas de Oro para todas las figuritas. <b>Camino libre para ahorrar en pesos.</b></div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""<div class="logic-card" style="border-left-color: #f29900;"><h4>🇺🇸 Informe Profundo de EE.UU.</h4>
        • <b>Tasa Bonos 10 años (TNX):</b> {tasa_usa:.2f}%<br>
        • <b>Estado del Imán:</b> {'🔴 FUERTE' if tasa_usa > 4.2 else '🟢 DÉBIL'}</div>""", unsafe_allow_html=True)
        
        # EXPLICACIÓN DINÁMICA NIÑO - EEUU
        if tasa_usa > 4.2:
            st.markdown(f"""<div class="mentor-note"><b>🏫 Lógica de la Escuela:</b> El dueño de la fábrica de Oro subió el premio a {tasa_usa:.2f}%. Es un imán gigante que se lleva los dólares de nuestra escuela hacia la de él.</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="mentor-note"><b>🏫 Lógica de la Escuela:</b> El imán está apagado. El dueño de la fábrica no está pidiendo Oro de vuelta. Hay aire para nosotros.</div>""", unsafe_allow_html=True)

    # --- PANEL FINAL DE VEREDICTO ---
    st.write("---")
    st.subheader("💡 Conclusión para no olvidarte:")
    if status == "NEUTRAL":
        st.info(f"El bot dice NEUTRAL porque el Riesgo País ({riesgo:.0f}) muestra que los niños están tranquilos, pero la Tasa de EEUU ({tasa_usa:.2f}%) y la falta de respaldo (${dolar_teorico:.0f}) te prohíben ganar tasa en pesos. **No hay ventaja: Espera.**")
    elif status == "PROTECCIÓN CRÍTICA":
        st.error("El imán de EEUU y la falta de respaldo en la caja fuerte ganaron la pelea. Sal de figuritas (pesos) antes de que el dólar pegue el salto.")
    elif status == "CARRY TRADE":
        st.success("El mundo está en paz y nuestra caja fuerte tiene respaldo. Es el momento de ganar alfajores (tasa) en pesos.")

except Exception as e:
    st.error(f"Sincronizando... {e}")
