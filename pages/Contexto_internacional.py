import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SLY v14.1: Robust Vision", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .command-box { padding: 30px; border-radius: 20px; text-align: center; color: white; margin-bottom: 25px; }
    .school-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 10px solid #2196f3; margin-top: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_institutional_data():
    # Tickers: ORO, DXY, Real Brasil, Galicia ADR, Galicia Local, Tasa USA 10Y
    tkrs = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA", "UST10Y": "^TNX"}
    try:
        df = yf.download(list(tkrs.values()), period="60d", interval="1d", progress=False)['Close']
        # Limpieza profunda para evitar gráficos vacíos
        df = df.ffill().bfill()
        return df
    except:
        return pd.DataFrame()

try:
    st.title("🛡️ SLY Engine: Terminal v14.1 - Robust Vision")
    df = fetch_institutional_data()
    
    if not df.empty:
        # --- CÁLCULOS ---
        ccl = (df["GGAL.BA"].iloc[-1] / df["GGAL"].iloc[-1]) * 10
        tasa_usa = df["^TNX"].iloc[-1]
        
        # Riesgo País via API
        res_r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=3).json()
        riesgo = float(res_r['valor'])
        
        dolar_respaldo = ccl * (1 + (riesgo / 10000))
        brecha_respaldo = ((dolar_respaldo / ccl) - 1) * 100
        tasa_ar_mensual = 3.5 

        # --- MOTOR DE DECISIÓN ---
        score = 0
        if tasa_usa > 4.4: score -= 30
        if brecha_respaldo > 5: score -= 20
        if riesgo < 750: score += 20

        if score <= -40: status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES YA"
        elif score >= 25: status, color, action = "CARRY TRADE", "#188038", "GANAR INTERESES EN PESOS"
        else: status, color, action = "NEUTRAL", "#007bff", "QUÉDATE QUIETO / ESPERA"

        # --- UI: MANDOS ---
        st.markdown(f"""<div class="command-box" style="background-color: {color};"><h1>{status}</h1><h2>{action}</h2></div>""", unsafe_allow_html=True)

        # --- MONITOR DE DULCES ---
        st.subheader("🍭 El Monitor de Dulces (Tasa vs Riesgo)")
        c_sweets, c_logic = st.columns([1, 2])
        with c_sweets:
            st.metric("Premio Mensual (Dulces)", f"{tasa_ar_mensual}%")
            st.metric("Riesgo Salto Dólar", f"{brecha_respaldo:.1f}%", delta_color="inverse")
        with c_logic:
            st.markdown(f"""<div class="school-card"><b>🏫 Veredicto del Alfajor:</b><br>
            {'❌ El peligro es mayor que el premio. No aceptes los dulces del Director.' if brecha_respaldo > tasa_ar_mensual else '✅ El premio es mayor al riesgo por ahora.'}
            <br><br><i>El dólar teórico es de ${dolar_respaldo:.0f} (Hoy pagas ${ccl:.0f})</i></div>""", unsafe_allow_html=True)

        # --- GRÁFICO (RECONSTRUIDO) ---
        st.subheader("📈 Mapa de Fuerzas Globales (Base 100)")
        
        fig = go.Figure()
        
        # Función de normalización segura (Evita divisiones por NaN o Cero)
        def get_norm_series(col_name):
            series = df[col_name].dropna()
            if not series.empty and series.iloc[0] != 0:
                return (series / series.iloc[0]) * 100
            return None

        # Dibujar líneas solo si hay datos
        oro_line = get_norm_series("GC=F")
        if oro_line is not None:
            fig.add_trace(go.Scatter(x=oro_line.index, y=oro_line, name="ORO", line=dict(color='#d4af37', width=3)))
        
        dxy_line = get_norm_series("DX-Y.NYB")
        if dxy_line is not None:
            fig.add_trace(go.Scatter(x=dxy_line.index, y=dxy_line, name="DXY (Dólar)", line=dict(color='#004a99', width=2)))
            
        iman_line = get_norm_series("^TNX")
        if iman_line is not None:
            fig.add_trace(go.Scatter(x=iman_line.index, y=iman_line, name="IMÁN EEUU", line=dict(color='#f44336', dash='dot')))

        fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', height=500,
            xaxis=dict(showgrid=True, gridcolor='#f1f1f1'),
            yaxis=dict(showgrid=True, gridcolor='#f1f1f1', title="Escala de Fuerza"),
            margin=dict(l=0,r=0,t=20,b=0),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("No hay conexión con la red de datos. Reintenta en unos segundos.")

except Exception as e:
    st.error(f"Error en el sistema: {e}")

st.button("🔄 ACTUALIZAR SISTEMA")
