import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE LA ESCUELA (INTERFAZ) ---
st.set_page_config(page_title="SLY v13.0: Storyteller Edition", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .command-box { padding: 30px; border-radius: 20px; text-align: center; color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .school-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 10px solid #2196f3; margin-top: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .child-explanation { font-size: 1.1em; color: #1e4976; line-height: 1.5; }
    .emoji-title { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; display: block; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_institutional_data():
    # Tickers: Oro, DXY, Brasil, Galicia ADR, Galicia Local, Tasa USA 10 años
    tkrs = {"ORO": "GC=F", "DXY": "DX-Y.NYB", "BRL": "USDBRL=X", "ADR": "GGAL", "LOCAL": "GGAL.BA", "UST10Y": "^TNX"}
    df = yf.download(list(tkrs.values()), period="30d", interval="1d", progress=False)['Close'].ffill()
    return df, tkrs

try:
    st.title("🛡️ SLY Engine: Terminal de Inteligencia v13.0")
    st.markdown("### El Reloj de la Verdad (Explicado para todos)")
    
    df, tkrs = fetch_institutional_data()
    
    # --- CÁLCULOS QUANTS ---
    ccl = (df["GGAL.BA"].iloc[-1] / df["GGAL"].iloc[-1]) * 10
    tasa_usa = df["^TNX"].iloc[-1]
    res_r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", timeout=3).json()
    riesgo = float(res_r['valor'])
    dolar_respaldo = ccl * (1 + (riesgo / 10000))

    # --- MOTOR DE DECISIÓN ---
    score = 0
    if tasa_usa > 4.4: score -= 30
    if dolar_respaldo > ccl * 1.05: score -= 20
    if riesgo > 1200: score -= 20

    if score <= -40: status, color, action, emoji = "PROTECCIÓN CRÍTICA", "#d93025", "COMPRA DÓLARES YA", "🚨"
    elif score >= 20: status, color, action, emoji = "CARRY TRADE", "#188038", "GANAR INTERESES EN PESOS", "🚲"
    else: status, color, action, emoji = "NEUTRAL", "#007bff", "QUÉDATE QUIETO / ESPERA", "⏳"

    # --- UI: EL CARTEL DE MANDO ---
    st.markdown(f"""
        <div class="command-box" style="background-color: {color};">
            <h1 style="margin:0; font-size: 3em; border:none;">{emoji} {status}</h1>
            <h2 style="margin:0; opacity:0.9; border:none;">{action}</h2>
        </div>
        """, unsafe_allow_html=True)

    # --- LA EXPLICACIÓN DEL NIÑO (DINÁMICA) ---
    st.subheader("🏫 El Cuento de hoy en la Escuela")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="school-card">', unsafe_allow_html=True)
        st.markdown('<span class="emoji-title">🇦🇷 Nuestras Figuritas y la Caja Fuerte</span>', unsafe_allow_html=True)
        
        # Lógica de las figuritas (Argentina)
        if dolar_respaldo > ccl:
            ar_story = f"El Director de nuestra escuela está regalando demasiadas **figuritas (Pesos)**, pero en la **Caja Fuerte** no tiene suficiente **Oro**. Por eso, el Dólar real de ${ccl:.0f} es una mentira, y el de verdad debería ser de ${dolar_respaldo:.0f}."
        else:
            ar_story = "El Director se está portando bien. No está regalando figuritas de más y la Caja Fuerte tiene suficiente Oro para todos. Los ahorros en pesos están tranquilos."
        
        st.markdown(f'<p class="child-explanation">{ar_story}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="school-card" style="border-left-color: #f29900;">', unsafe_allow_html=True)
        st.markdown('<span class="emoji-title">🇺🇸 El Imán de la Escuela de al Lado</span>', unsafe_allow_html=True)
        
        # Lógica del imán (EEUU)
        if tasa_usa > 4.2:
            us_story = f"El dueño de la fábrica de Oro (EEUU) puso un **imán gigante** (Tasa de {tasa_usa:.2f}%). Ese imán tiene mucha fuerza y se quiere llevar nuestras cartas de oro hacia su escuela. Esto hace que el Dólar quiera subir aquí."
        else:
            us_story = "El imán de la fábrica de Oro está apagado. No tienen interés en llevarse nuestro oro, así que podemos jugar tranquilos por ahora."
            
        st.markdown(f'<p class="child-explanation">{us_story}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- EL PORQUÉ FINAL ---
    st.write("---")
    st.markdown("### 💡 ¿Por qué el bot tomó esta decisión?")
    
    if status == "NEUTRAL":
        st.info(f"**Análisis de SystemaTrader:** Hoy es un empate. El imán de afuera tira con fuerza ({tasa_usa:.2f}%), pero en la escuela los niños están tranquilos (Riesgo País {riesgo:.0f} pts). Como nadie gana la pelea, el bot te dice que **no apuestes** y esperes a que alguien gane.")
    elif status == "PROTECCIÓN CRÍTICA":
        st.error(f"**Análisis de SystemaTrader:** ¡Peligro! El imán está muy fuerte y el Director no tiene nada en la caja fuerte. Las figuritas van a perder su valor muy pronto. **¡Cambia tus figuritas por Oro (Dólar/USDT) ya!**")
    elif status == "CARRY TRADE":
        st.success(f"**Análisis de SystemaTrader:** ¡Oportunidad! El imán está apagado y la caja fuerte está llena. Aprovecha para ganar los dulces (intereses) que regala el Director por quedarte en figuritas.")

    # --- MÉTRICAS ---
    st.write("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio Dólar", f"${ccl:,.1f}")
    m2.metric("Fuerza del Imán (Tasa)", f"{tasa_usa:.2f}%")
    m3.metric("Confianza (Riesgo)", f"{riesgo:.0f} pts")
    m4.metric("Dólar de Verdad", f"${dolar_respaldo:,.0f}")

except Exception as e:
    st.error(f"Sincronizando la escuela... {e}")

st.button("🔄 ACTUALIZAR EL CUENTO")
