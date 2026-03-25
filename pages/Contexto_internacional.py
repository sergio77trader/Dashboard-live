import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SLY: Decision Forensics", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .forensic-card { background-color: white; padding: 25px; border-radius: 15px; border-top: 5px solid #004a99; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .factor-tag { padding: 5px 12px; border-radius: 20px; font-size: 0.9em; font-weight: bold; margin-right: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_institutional_data():
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "SOJA": "ZS=F"
    }
    df = yf.download(list(symbols.values()), period="60d", interval="1d", progress=False)['Close']
    return df.ffill().bfill(), symbols

try:
    df, symbols = fetch_institutional_data()
    
    def get_stats(key):
        current = df[symbols[key]].iloc[-1]
        sma20 = df[symbols[key]].rolling(20).mean().iloc[-1]
        change_pct = ((current / df[symbols[key]].iloc[-2]) - 1) * 100
        return current, sma20, change_pct

    ccl_now = (df[symbols["LOCAL"]].iloc[-1] / df[symbols["ADR"]].iloc[-1]) * 10
    oro_p, oro_sma, oro_ch = get_stats("ORO")
    dxy_p, dxy_sma, dxy_ch = get_stats("DXY")
    brl_p, brl_sma, brl_ch = get_stats("BRL")
    soja_p, soja_sma, soja_ch = get_stats("SOJA")

    # --- MOTOR FORENSE (CÁLCULO DE PUNTOS) ---
    points = []
    total_score = 0

    # 1. Análisis Dólar Global
    if dxy_p > dxy_sma:
        total_score -= 35
        points.append(("🔴 DXY > Promedio", "-35 pts", "El dólar global está fuerte, succionando capital de emergentes."))
    else:
        total_score += 10
        points.append(("🟢 DXY bajo control", "+10 pts", "La presión global de EE.UU. es baja."))

    # 2. Análisis Brasil
    if brl_ch > 0.4:
        total_score -= 30
        points.append(("🔴 Devaluación Brasil", "-30 pts", "Brasil está devaluando fuerte hoy, forzando al peso a seguirlo."))
    elif brl_p < brl_sma:
        total_score += 15
        points.append(("🟢 Real Fuerte", "+15 pts", "Nuestro principal socio comercial está estable."))

    # 3. Análisis Oro (Refugio)
    if oro_p > oro_sma:
        total_score += 25
        points.append(("🟢 Oro en Tendencia", "+25 pts", "El Oro valida que el dólar global está perdiendo valor real."))
    else:
        total_score -= 10
        points.append(("🟡 Oro Débil", "-10 pts", "No hay refugio activo contra el dólar global."))

    # 4. Análisis Soja (Caja Fuerte)
    if soja_p < soja_sma:
        total_score -= 20
        points.append(("🔻 Soja a la baja", "-20 pts", "Menos ingresos proyectados por exportaciones agrícolas."))

    # --- DETERMINACIÓN DE ESTADO ---
    if total_score <= -40:
        status, color, action = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES / CRIPTO YA"
    elif total_score >= 25:
        status, color, action = "CARRY TRADE ACTIVO", "#188038", "MANTÉN PESOS (LECAPS / PLAZO FIJO)"
    else:
        status, color, action = "POSICIÓN NEUTRAL", "#007bff", "MANTÉN TUS POSICIONES ACTUALES"

    # --- UI: PANEL DE MANDO ---
    st.markdown(f"""
        <div style="background-color: {color}; padding: 20px; border-radius: 15px 15px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0;">{status}</h1>
            <h2 style="color: white; opacity: 0.9; margin: 0;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- UI: PANEL FORENSE ---
    with st.container():
        st.markdown(f"""
        <div class="forensic-card">
            <h3>🔍 Forense de Decisión (Puntaje Total: {total_score})</h3>
            <p>Por qué el sistema toma esta decisión hoy:</p>
        """, unsafe_allow_html=True)
        
        for title, pts, desc in points:
            dot_color = "red" if "-" in pts else "green"
            st.markdown(f"**{title}** ({pts}): {desc}")
        
        st.markdown("</div>", unsafe_allow_html=True)

    # --- MÉTRICAS ---
    st.write("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar CCL", f"${ccl_now:,.1f}")
    c2.metric("Oro (XAU)", f"${oro_p:,.0f}")
    c3.metric("DXY Global", f"{dxy_p:.2f}", delta_color="inverse")
    c4.metric("Dólar Brasil", f"{brl_p:.3f}", delta_color="inverse")

    # --- GRÁFICO ---
    st.subheader("📊 Visualización de Convergencia (60 Días)")
    def norm(s): return (s / s.iloc[0]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["ORO"]]), name="ORO", line=dict(color='#d4af37', width=3)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["DXY"]]), name="DXY (USA)", line=dict(color='#004a99')))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["BRL"]]), name="BRL (Brasil)", line=dict(color='#188038')))
    fig.update_layout(plot_bgcolor='white', height=450, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Sincronizando con los servidores de datos... {e}")
