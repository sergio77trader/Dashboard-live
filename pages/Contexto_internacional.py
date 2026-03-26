import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SLY v12.0: Central Bank Monitor", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .command-box { padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .logic-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 10px solid #004a99; margin-top: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_institutional_data():
    # Agregamos ^TNX (Tasa 10 años USA) para informe profundo de EEUU
    tkrs = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA", "UST10Y": "^TNX"}
    df = yf.download(list(tkrs.values()), period="30d", interval="1d", progress=False)['Close'].ffill()
    return df, tkrs

try:
    st.title("🛡️ SLY Engine: Intelligence Terminal v12.0")
    df, tkrs = fetch_institutional_data()
    
    # --- CÁLCULOS QUANTS ---
    ccl = (df["GGAL.BA"].iloc[-1] / df["GGAL"].iloc[-1]) * 10
    dxy = df["DX-Y.NYB"].iloc[-1]
    brl = df["USDBRL=X"].iloc[-1]
    tasa_usa = df["^TNX"].iloc[-1]
    
    # --- MOTOR DE EMISIÓN (SIMULACIÓN DE RESPALDO) ---
    # En un sistema real, aquí conectaríamos con la API del BCRA. 
    # Usamos el Riesgo País como proxy de desconfianza monetaria.
    res_r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=3).json()
    riesgo = float(res_r['valor'])
    
    # Dólar de Convertibilidad Estimado (Basado en desvío de Riesgo País)
    # Si el riesgo sube, el dólar "teórico" se aleja del real.
    dolar_teorico = ccl * (1 + (riesgo / 10000))

    # --- MOTOR DE DECISIÓN v12.0 ---
    score = 0
    reasons = []
    
    if tasa_usa > 4.5: 
        score -= 30
        reasons.append(f"⚠️ EEUU AGRESIVO: Tasa 10Y en {tasa_usa:.2f}%. Succión de capitales.")
    if dolar_teorico > ccl * 1.05:
        score -= 20
        reasons.append(f"💸 ALERTA MONETARIA: El dólar de mercado (${ccl:.0f}) está barato vs el respaldo (${dolar_teorico:.0f}).")
    if brl > 5.25:
        score -= 20
        reasons.append("🇧🇷 BRASIL DEVALUANDO: Presión por competencia regional.")

    # --- DETERMINACIÓN DE ESTADO ---
    if score <= -40: status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES / USDT YA"
    elif score >= 15: status, color, action = "CARRY TRADE", "#188038", "GANAR TASA EN PESOS"
    else: status, color, action = "NEUTRAL", "#007bff", "SIN CAMBIOS OPERATIVOS"

    # --- UI: RENDERIZADO ---
    st.markdown(f"""<div class="command-box" style="background-color: {color};"><h1>{status}</h1><h2>{action}</h2></div>""", unsafe_allow_html=True)

    # --- NUEVO PANEL DE DETALLES ---
    st.subheader("🔍 Auditoría de la Decisión")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""<div class="logic-card"><h4>🇦🇷 Monitor de Emisión y Respaldo</h4>
        • <b>Dólar Real:</b> ${ccl:.1f}<br>
        • <b>Dólar de Respaldo (Teórico):</b> ${dolar_teorico:.1f}<br>
        • <b>Riesgo País:</b> {riesgo:.0f} pts<br>
        <i>{'⚠️ El Director está emitiendo sin respaldo real.' if dolar_teorico > ccl else '✅ El peso tiene respaldo suficiente.'}</i></div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="logic-card" style="border-left-color: #f29900;"><h4>🇺🇸 Informe Profundo de EE.UU.</h4>
        • <b>DXY Index:</b> {dxy:.2f}<br>
        • <b>Tasa Bonos 10 años (TNX):</b> {tasa_usa:.2f}%<br>
        • <b>Estado del Imán:</b> {'🔴 FUERTE (Aspirando dólares)' if tasa_usa > 4.2 else '🟢 DÉBIL'}<br>
        <i>{'El mundo prefiere los bonos de EEUU que los activos de riesgo.' if tasa_usa > 4.2 else 'Hay liquidez para mercados emergentes.'}</i></div>""", unsafe_allow_html=True)

    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dólar CCL", f"${ccl:,.1f}")
    m2.metric("Tasa USA 10Y", f"{tasa_usa:.2f}%")
    m3.metric("Dólar Brasil", f"{brl:.3f}")
    m4.metric("Riesgo País", f"{riesgo:.0f}")

except Exception as e:
    st.error(f"Sincronizando con los servidores... {e}")

st.button("🔄 ACTUALIZAR INTELIGENCIA")
