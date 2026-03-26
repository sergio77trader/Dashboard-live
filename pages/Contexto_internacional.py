import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SLY v8.4: Bulletproof Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .forensic-card { background-color: white; padding: 20px; border-radius: 15px; border-left: 8px solid #004a99; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .arbitrage-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border: 1px solid #004a99; color: #004a99; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_institutional_data():
    # Diccionario de tickers. Usamos GLD para oro por estabilidad.
    symbols_map = {
        "GLD": "GLD", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "AL30": "AL30.BA", "AL30D": "AL30D.BA"
    }
    try:
        # Descarga masiva (una sola llamada al servidor para evitar bloqueos)
        raw_data = yf.download(list(symbols_map.values()), period="30d", interval="1d", progress=False)['Close']
        # Limpieza: Llenamos huecos y eliminamos filas totalmente vacías
        clean_df = raw_data.ffill().dropna(how='all')
        return clean_df, symbols_map
    except Exception as e:
        st.error(f"Fallo en Data Feed: {e}")
        return pd.DataFrame(), symbols_map

try:
    df, syms = fetch_institutional_data()

    if not df.empty:
        # Extraemos el último valor real disponible para cada activo (sin ceros)
        def get_actual(key):
            ticker = syms[key]
            series = df[ticker].dropna()
            return float(series.iloc[-1]) if not series.empty else 0.0

        # --- CÁLCULOS QUANTS ---
        val_oro = get_actual("GLD") * 10 # Ajuste para que se vea como onza
        val_dxy = get_actual("DXY")
        val_brl = get_actual("BRL")
        val_adr = get_actual("ADR")
        val_local = get_actual("LOCAL")
        val_al30 = get_actual("AL30")
        val_al30d = get_actual("AL30D")

        # Ratios de Dólar
        ccl = (val_local / val_adr) * 10 if val_adr > 0 else 0
        mep = (val_al30 / val_al30d) if val_al30d > 0 else 0
        risk_proxy = 100 / val_al30d if val_al30d > 0 else 0

        # --- MOTOR DE DECISIÓN ---
        score = 0
        if val_dxy > 100: score -= 25
        if val_brl > 5.20: score -= 25
        if val_al30d < 38: score -= 30 # Miedo local

        if score <= -40:
            status, color, action = "ALERTA CRÍTICA", "#d93025", "COMPRA DÓLAR / USDT - PROTECCIÓN"
        elif score >= 20:
            status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS - OPORTUNIDAD"
        else:
            status, color, action = "POSICIÓN NEUTRAL", "#007bff", "MANTÉN TUS POSICIONES"

        # --- UI: PANEL DE MANDO ---
        st.markdown(f"""
            <div style="background-color: {color}; padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom:20px;">
                <h1 style="margin:0;">{status}</h1>
                <h2 style="opacity:0.9; margin:0;">{action}</h2>
            </div>
            """, unsafe_allow_html=True)

        # --- UI: ARBITRAJE ---
        col_arb1, col_arb2 = st.columns(2)
        with col_arb1:
            spread = ((ccl / mep) - 1) * 100 if mep > 0 else 0
            st.markdown(f"""<div class="arbitrage-box">⚖️ SPREAD CCL vs MEP: {spread:.1f}%<br>RECOMENDACIÓN: {'Comprar MEP / USDT' if spread > 1.5 else 'Precios equilibrados'}</div>""", unsafe_allow_html=True)
        with col_arb2:
            st.markdown(f"""<div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">🛰️ RIESGO PAÍS PROXY: {risk_proxy:.2f}<br>ESTADO: {'🔴 PRESIÓN ALTA' if risk_proxy > 2.6 else '🟢 ESTABLE'}</div>""", unsafe_allow_html=True)

        # --- UI: MÉTRICAS ---
        st.write("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dólar CCL", f"${ccl:,.1f}")
        m1.metric("Dólar MEP", f"${mep:,.1f}")
        m2.metric("Oro (XAU ETF)", f"${val_oro:,.0f}")
        m3.metric("DXY Index", f"{val_dxy:.2f}")
        m4.metric("Dólar Brasil", f"{val_brl:.3f}")

        # --- UI: GRÁFICO ---
        st.subheader("📊 Gráfico de Convergencia (Base 100)")
        def norm(s): return (df[syms[s]] / df[syms[s]].dropna().iloc[0]) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=norm("GLD"), name="ORO", line=dict(color='#d4af37', width=3)))
        fig.add_trace(go.Scatter(x=df.index, y=norm("DXY"), name="DXY", line=dict(color='#004a99')))
        fig.add_trace(go.Scatter(x=df.index, y=norm("AL30D"), name="BONO USD", line=dict(color='#d93025', dash='dot')))
        fig.update_layout(plot_bgcolor='white', height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Aguardando respuesta de los servidores globales de Yahoo Finance...")

except Exception as e:
    st.error(f"Error crítico en terminal: {e}")

st.info("SystemaTrader v8.4: Protocolo de descarga masiva activado. Los datos del MEP y Oro están sincronizados con el último cierre.")info("SystemaTrader v8.3: Error de ambigüedad resuelto. El sistema ahora garantiza valores escalares para la toma de decisiones.")
