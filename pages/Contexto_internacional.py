import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE INTERFAZ ---
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
    symbols = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA"}
    df = yf.download(list(symbols.values()), period="5d", interval="1h", progress=False)['Close']
    return df.ffill().bfill(), symbols

df, symbols = fetch_data()

if df is not None:
    # --- CÁLCULOS SEGUROS ---
    adr_now = df[symbols["ADR"]].iloc[-1]
    local_now = df[symbols["LOCAL"]].iloc[-1]
    
    # Ajuste de Ratio (GGAL ADR es 1 ADR = 10 Locales)
    # Si el resultado es muy bajo, corregimos escala automáticamente
    ccl = (adr_now * 10) / local_now
    if ccl < 10: ccl = ccl * 1000 # Corrección para tickers en pesos/centavos

    dxy_ch = ((df[symbols["DXY"]].iloc[-1] / df[symbols["DXY"]].iloc[-2]) - 1) * 100
    brl_ch = ((df[symbols["BRL"]].iloc[-1] / df[symbols["BRL"]].iloc[-2]) - 1) * 100
    oro_ch = ((df[symbols["ORO"]].iloc[-1] / df[symbols["ORO"]].iloc[-2]) - 1) * 100

    # --- MOTOR DE DECISIÓN (LÓGICA DE MANDO) ---
    score = 0
    if dxy_ch > 0.3: score -= 30
    if brl_ch > 0.5: score -= 30
    if oro_ch > 0.2: score += 20
    
    if score <= -40:
        decision, color, msg = "🛡️ COBERTURA TOTAL", "#d93025", "PELIGRO: El mundo busca dólares. Sal de pesos inmediatamente."
    elif score >= 30:
        decision, color, msg = "🚲 CARRY TRADE ACTIVO", "#188038", "OPORTUNIDAD: Gana tasa en pesos. El dólar global está débil."
    else:
        decision, color, msg = "⏳ NEUTRAL / ESPERAR", "#00aaff", "Mercado sin tendencia clara. Mantén posición actual."

    # --- UI: COMANDO PRINCIPAL ---
    st.markdown(f"""
        <div class="command-box" style="background-color: {color}15; border: 2px solid {color};">
            <h1 style="color: {color}; margin: 0;">{decision}</h1>
            <h3 style="color: #3c4043;">{msg}</h3>
        </div>
        """, unsafe_allow_html=True)

    # --- INFO DETALLADA (EL PORQUÉ) ---
    st.subheader("🔍 Análisis Detallado de Factores")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"""
        <div class="detail-card">
            <h4>🌍 Contexto Global</h4>
            <ul>
                <li><b>DXY (Dólar):</b> {'📈 Subiendo (Malo para ARS)' if dxy_ch > 0 else '📉 Bajando (Bueno para ARS)'}</li>
                <li><b>ORO (Refugio):</b> {'✅ Validando debilidad' if oro_ch > 0 else '❌ Sin fuerza de refugio'}</li>
                <li><b>Brasil (BRL):</b> {'⚠️ Devaluando (Presión)' if brl_ch > 0.3 else '✅ Estable'}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""
        <div class="detail-card" style="border-left-color: #f29900;">
            <h4>🇦🇷 Situación Local</h4>
            <ul>
                <li><b>Dólar CCL Real:</b> ${ccl:,.2f}</li>
                <li><b>Brecha Estimada:</b> {round(((ccl/1000)-1)*100, 2) if ccl > 1000 else 'Calculando...'}%</li>
                <li><b>ADR GGAL:</b> {'🔻 Fuga detectada' if adr_now < df[symbols['ADR']].iloc[-2] else '🟢 Sin presión de venta'}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # --- MÉTRICAS RÁPIDAS ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar CCL", f"${ccl:,.2f}")
    c2.metric("Oro (XAU)", f"${df[symbols['ORO']].iloc[-1]:.1f}", f"{oro_ch:+.2f}%")
    c3.metric("DXY Global", f"{df[symbols['DXY']].iloc[-1]:.2f}", f"{dxy_ch:+.2f}%", delta_color="inverse")
    c4.metric("Dólar Brasil", f"{df[symbols['BRL']].iloc[-1]:.3f}", f"{brl_ch:+.2f}%", delta_color="inverse")

    # --- GRÁFICO ---
    st.subheader("📈 Gráfico de Convergencia (Base 100)")
    def norm(col): return (df[col] / df[col].iloc[0]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["ORO"]), name="ORO", line=dict(color='#d4af37', width=3)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["DXY"]), name="DXY (EE.UU)", line=dict(color='#004a99')))
    fig.add_trace(go.Scatter(x=df.index, y=norm(symbols["BRL"]), name="REAL (Brasil)", line=dict(color='#188038')))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=400, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

st.button("🔄 Actualizar Inteligencia")
