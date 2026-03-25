import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SYSTEMATRADER: Decision Engine", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .stMetric { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #d1d5db; }
    .directive-box { padding: 25px; border-radius: 15px; margin-bottom: 20px; border-left: 10px solid; }
    .directive-title { font-size: 1.8em; font-weight: bold; }
    .directive-text { font-size: 1.1em; color: #333; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_institutional_data():
    symbols = {
        "ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", 
        "ADR": "GGAL", "LOCAL": "GGAL.BA", "SOJA": "ZS=F"
    }
    # Ampliamos a 60 días para tener contexto de tendencia
    df = yf.download(list(symbols.values()), period="60d", interval="1d", progress=False)['Close']
    return df.ffill().bfill(), symbols

try:
    df, symbols = fetch_institutional_data()
    
    # --- CÁLCULOS DE MOMENTUM ---
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

    # --- MOTOR DE RECOMENDACIÓN (LOGIC GATES) ---
    score = 0
    # Regla 1: DXY por encima de su promedio = Succión de dólares (Malo)
    if dxy_p > dxy_sma: score -= 30
    # Regla 2: Oro por encima de su promedio = Dólar global débil (Bueno)
    if oro_p > oro_sma: score += 25
    # Regla 3: Brasil devaluando fuerte hoy
    if brl_ch > 0.5: score -= 25
    # Regla 4: Soja cayendo (Menos reservas)
    if soja_p < soja_sma: score -= 20

    # --- DETERMINACIÓN DE INSTRUCCIÓN ---
    if score <= -40:
        status, color, action = "🛡️ PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES / CRIPTO YA. El contexto macro es de tormenta. No mantengas pesos."
    elif score >= 20:
        status, color, action = "🚲 CARRY TRADE (SOLO AGRESIVOS)", "#188038", "MANTÉN PESOS A TASA. El mundo y el Oro validan estabilidad temporal. Monitoreo diario obligatorio."
    else:
        status, color, action = "⏳ POSICIÓN NEUTRAL", "#007bff", "MANTÉN TUS POSICIONES. No hay ventaja clara para cambiar de moneda hoy."

    # --- UI: INSTRUCCIONES EJECUTIVAS ---
    st.markdown(f"""
        <div class="directive-box" style="background-color: {color}10; border-color: {color};">
            <div class="directive-title" style="color: {color};">{status}</div>
            <div class="directive-text"><b>ORDEN DEL SISTEMA:</b> {action}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- DASHBOARD DE MÉTRICAS ---
    st.subheader("🔍 Estado de los 'Espías' de Mercado")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dólar CCL", f"${ccl_now:,.1f}", f"{((ccl_now/df[symbols['LOCAL']].iloc[-2]/df[symbols['ADR']].iloc[-2]*10)-1)*100:+.2f}%")
    c2.metric("Oro (XAU/USD)", f"${oro_p:,.0f}", f"{oro_ch:+.2f}%", help="Si el Oro sube, el Dólar global está perdiendo valor real.")
    c3.metric("DXY Global", f"{dxy_p:.2f}", f"{dxy_ch:+.2f}%", delta_color="inverse", help="Si el DXY sube, Argentina se queda sin dólares.")
    c4.metric("Dólar Brasil", f"{brl_p:.3f}", f"{brl_ch:+.2f}%", delta_color="inverse")

    # --- ANÁLISIS DE TENDENCIA ---
    st.subheader("📊 Comparativa de Tendencia (Últimos 60 días)")
    def norm(series): return (series / series.iloc[0]) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["ORO"]]), name="ORO (Tendencia)", line=dict(color='#FFD700', width=3)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["DXY"]]), name="DXY (EE.UU)", line=dict(color='#1E90FF', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=norm(df[symbols["BRL"]]), name="Brasil", line=dict(color='#32CD32', width=2)))
    
    fig.update_layout(plot_bgcolor='white', height=500, margin=dict(l=10,r=10,t=10,b=10), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **¿Por qué este gráfico es diferente?**
    Aquí ves quién le está ganando a quién en los últimos 2 meses. Si la línea **Azul (DXY)** sube más que las otras, la presión sobre el peso argentino es **insostenible**.
    """)

except Exception as e:
    st.error(f"Sincronizando con los servidores de Londres y Nueva York... {e}")

if st.button('🔄 Forzar Recálculo de Estrategia'):
    st.cache_data.clear()
    st.rerun()
