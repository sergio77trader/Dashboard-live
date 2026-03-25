import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE INTERFAZ INSTITUCIONAL (LIGHT THEME) ---
st.set_page_config(page_title="SLY: Macro Truth Monitor", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1c1e21; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stMetricValue"] { color: #004a99 !important; font-weight: bold; }
    .command-box { padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #002d5a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ SLY Engine: Macro Truth Monitor v4.1")
st.markdown("---")

@st.cache_data(ttl=600)
def fetch_data_resilient():
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", 
        "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA"
    }
    # Intentamos 1h para mayor estabilidad si 15m falla
    try:
        df = yf.download(list(symbols.values()), period="5d", interval="1h", progress=False)['Close']
        # Limpieza de NaNs: Llenamos huecos con el último valor conocido
        df = df.ffill().bfill()
        return df, symbols
    except:
        return None, None

df, symbols = fetch_data_resilient()

if df is not None and not df.empty:
    try:
        # --- EXTRACCIÓN SEGURA DE VALORES ---
        def get_last(sym): return df[symbols[sym]].iloc[-1]
        def get_prev(sym): return df[symbols[sym]].iloc[-2]

        # 1. CÁLCULO DÓLAR CCL
        # Verificamos que no sean nulos para evitar el nan
        adr_now = get_last("ADR")
        local_now = get_last("LOCAL")
        ccl = (adr_now * 10) / local_now if local_now > 0 else 0
        
        # 2. VARIACIONES
        oro_now = get_last("ORO")
        oro_ch = ((oro_now / get_prev("ORO")) - 1) * 100
        
        dxy_now = get_last("DXY")
        dxy_ch = ((dxy_now / get_prev("DXY")) - 1) * 100
        
        brl_now = get_last("BRL")
        brl_ch = ((brl_now / get_prev("BRL")) - 1) * 100

        # --- LÓGICA DE MANDO ---
        decision, color, detalles = "NEUTRAL", "#00aaff", "No hay señales claras de desequilibrio."

        if dxy_ch > 0.4 or brl_ch > 0.6:
            decision, color, detalles = "🛡️ COBERTURA TOTAL", "#d93025", "Dólar global fuerte o Brasil devaluando. SAL DE PESOS AHORA."
        elif dxy_ch < 0 and oro_ch > 0.2:
            decision, color, detalles = "🚲 CARRY TRADE ACTIVO", "#188038", "Mundo estable y Oro fuerte. Buen momento para ganar tasa en Pesos."
        elif adr_now < get_prev("ADR") * 0.98:
            decision, color, detalles = "🚨 FUGA DE CAPITALES", "#f29900", "Fondos vendiendo ADRs en NY. Presión de subida inminente."

        # --- UI: CENTRO DE MANDOS ---
        st.markdown(f"""
            <div class="command-box" style="background-color: {color}15; border: 2px solid {color};">
                <h1 style="color: {color}; margin: 0; font-size: 2.5em;">{decision}</h1>
                <p style="color: #3c4043; font-size: 1.4em; margin-top: 15px;">{detalles}</p>
            </div>
            """, unsafe_allow_html=True)

        # --- MÉTRICAS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dólar CCL", f"${ccl:.2f}")
        c2.metric("Oro (XAU)", f"${oro_now:.1f}", f"{oro_ch:+.2f}%")
        c3.metric("DXY Global", f"{dxy_now:.2f}", f"{dxy_ch:+.2f}%", delta_color="inverse")
        c4.metric("Dólar Brasil", f"{brl_now:.3f}", f"{brl_ch:+.2f}%", delta_color="inverse")

        # --- GRÁFICO ---
        st.subheader("Tendencia de Activos (Base 100)")
        def norm(col): return (df[col] / df[col].iloc[0]) * 100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["ORO"]), name="ORO", line=dict(color='#d4af37', width=3)))
        fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["DXY"]), name="DXY (USA)", line=dict(color='#004a99')))
        fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["BRL"]), name="REAL (Brasil)", line=dict(color='#188038')))
        fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', 
            font=dict(color='#1c1e21'), height=500,
            xaxis=dict(showgrid=True, gridcolor='#f1f3f4'),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f4')
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error en el cálculo: {e}")
else:
    st.error("❌ ERROR CRÍTICO: No se pudo obtener data de Yahoo Finance. Reintenta en 1 minuto.")

if st.button('🔄 Refrescar Datos de Mercado'):
    st.cache_data.clear()
    st.rerun()
