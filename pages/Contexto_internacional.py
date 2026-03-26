import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="SLY v8.5: Terminal Macro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .command-box { padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .arbitrage-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border: 1px solid #004a99; color: #004a99; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS (RECOLECCIÓN) ---
@st.cache_data(ttl=600)
def fetch_all_data():
    # Tickers maestros: Oro (GLD), DXY, Brasil, Galicia, Bonos AL30
    tickers = {
        "GLD": "GLD", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X",
        "ADR": "GGAL", "LOCAL": "GGAL.BA", 
        "AL30": "AL30.BA", "AL30D": "AL30D.BA"
    }
    try:
        # Descarga única de 30 días para tener contexto histórico y evitar ceros
        df = yf.download(list(tickers.values()), period="30d", interval="1d", progress=False)['Close']
        df = df.ffill().bfill()
        return df, tickers
    except Exception as e:
        st.error(f"Fallo en la red de datos: {e}")
        return pd.DataFrame(), tickers

# --- 3. LÓGICA DE CÁLCULO ---
try:
    data_df, syms = fetch_all_data()

    if not data_df.empty:
        # Función para obtener el último valor limpio (evita NaNs y ceros)
        def get_val(key):
            ticker = syms[key]
            series = data_df[ticker].dropna()
            return float(series.iloc[-1]) if not series.empty else 0.0

        # Captura de valores actuales
        oro = get_val("GLD") * 10
        dxy = get_val("DXY")
        brl = get_val("BRL")
        adr = get_val("ADR")
        local = get_val("LOCAL")
        al30 = get_val("AL30")
        al30d = get_val("AL30D")

        # Ratios de Moneda
        # GGAL Ratio 1:10
        ccl = (local / adr) * 10 if adr > 0 else 0.0
        # MEP: Bono Pesos / Bono Dólares
        mep = (al30 / al30d) if al30d > 0 else 0.0
        # Riesgo País Proxy
        risk = 100 / al30d if al30d > 0 else 0.0

        # --- 4. MOTOR DE DECISIÓN SLY ---
        score = 0
        if dxy > 100: score -= 25
        if brl > 5.20: score -= 25
        if al30d < 38: score -= 30

        if score <= -40:
            status, color, action = "ALERTA CRÍTICA", "#d93025", "COMPRA DÓLAR / USDT - PROTECCIÓN"
        elif score >= 20:
            status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS - OPORTUNIDAD"
        else:
            status, color, action = "POSICIÓN NEUTRAL", "#007bff", "MANTÉN TUS POSICIONES"

        # --- 5. RENDERIZADO DE INTERFAZ ---
        st.title("🛡️ SLY Engine: Macro Truth Monitor v8.5")

        st.markdown(f"""
            <div class="command-box" style="background-color: {color};">
                <h1 style="margin:0; color:white; border:none;">{status}</h1>
                <h2 style="margin:0; color:white; opacity:0.9; border:none;">{action}</h2>
            </div>
            """, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            spread = ((ccl / mep) - 1) * 100 if mep > 0 else 0
            st.markdown(f"""<div class="arbitrage-box">⚖️ SPREAD CCL vs MEP: {spread:.1f}%<br>RECOMENDACIÓN: {'Comprar MEP / USDT' if spread > 1.5 else 'Equilibrado'}</div>""", unsafe_allow_html=True)
        with col_b:
            st.markdown(f"""<div class="arbitrage-box" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">🛰️ RIESGO PAÍS PROXY: {risk:.2f}<br>ESTADO: {'🔴 PRESIÓN ALTA' if risk > 2.6 else '🟢 ESTABLE'}</div>""", unsafe_allow_html=True)

        st.write("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dólar CCL", f"${ccl:,.1f}")
        m1.metric("Dólar MEP", f"${mep:,.1f}")
        m2.metric("Oro (XAU)", f"${oro:,.0f}")
        m3.metric("DXY Index", f"{dxy:.2f}")
        m4.metric("Dólar Brasil", f"{brl:.3f}")

        # --- 6. GRÁFICOS ---
        st.subheader("📈 Convergencia de Tendencias (Base 100)")
        def norm(k): return (data_df[syms[k]] / data_df[syms[k]].dropna().iloc[0]) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data_df.index, y=norm("GLD"), name="ORO", line=dict(color='#d4af37', width=3)))
        fig.add_trace(go.Scatter(x=data_df.index, y=norm("DXY"), name="DXY", line=dict(color='#004a99')))
        fig.add_trace(go.Scatter(x=data_df.index, y=norm("AL30D"), name="BONO USD", line=dict(color='#d93025', dash='dot')))
        fig.update_layout(plot_bgcolor='white', height=450, margin=dict(l=0,r=0,t=0,b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Fallo crítico en el cálculo: {e}")

if st.button('🔄 ACTUALIZAR SISTEMA'):
    st.cache_data.clear()
    st.rerun()
