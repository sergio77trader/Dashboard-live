import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - SLY ENGINE
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MONEY FLOW INTELLIGENCE", page_icon="🏦")

# CSS para Estética de Terminal Bloomberg/Dark
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    h1, h2, h3 { color: #00FFAA; font-family: 'Inter', sans-serif; }
    .metric-box { 
        background-color: #161B22; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #00FFAA;
        margin-bottom: 20px;
    }
    .stDataFrame { background-color: #161B22; }
</style>
""", unsafe_allow_html=True)

# DICCIONARIO MAESTRO EXPANDIDO (Sectores y Flujos)
MARKETS = {
    "Risk-On (Equities)": ["SPY", "QQQ", "IWM", "DIA"],
    "Sectores USA": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Defensivos & Metales": ["GLD", "SLV", "GDX", "TLT", "TIP"],
    "Global Flow": ["EEM", "EWZ", "FXI", "VGK", "FEZ"],
    "Crypto & High Beta": ["BTC-USD", "ETH-USD", "COIN", "MSTR", "ARKK"]
}

@st.cache_data(ttl=3600)
def get_institutional_data(tickers, start_date):
    # Descargamos Close y Volume para análisis de flujo
    df = yf.download(tickers, start=start_date, progress=False)
    close = df['Close'].ffill()
    volume = df['Volume'].ffill()
    return close, volume

# ─────────────────────────────────────────────
# CONTROL DE MANDOS
# ─────────────────────────────────────────────
st.title("🏦 SLY MONEY FLOW INTELLIGENCE")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ ENGINE CONFIG")
    lookback_period = st.selectbox("Ventana de Análisis:", 
                                   ["1 Mes", "3 Meses", "6 Meses", "YTD", "1 Año"], index=3)
    
    today = datetime.now()
    dates = {"1 Mes": 30, "3 Meses": 90, "6 Meses": 180, "YTD": (today - datetime(today.year, 1, 1)).days, "1 Año": 365}
    start = today - timedelta(days=dates[lookback_period])

    selected_cat = st.multiselect("Categorías de Flujo:", options=list(MARKETS.keys()), 
                                  default=["Sectores USA", "Risk-On (Equities)"])

# PROCESAMIENTO FORENSE
all_tickers = []
for cat in selected_cat:
    all_tickers.extend(MARKETS[cat])

if all_tickers:
    close_data, vol_data = get_institutional_data(all_tickers, start)
    
    # 1. Rendimiento Normalizado
    norm_data = (close_data / close_data.iloc[0] - 1) * 100
    
    # 2. Cálculo de RVOL (Relative Volume)
    # Comparamos volumen promedio de las últimas 5 sesiones vs el histórico de la ventana
    avg_vol_window = vol_data.mean()
    recent_vol = vol_data.iloc[-5:].mean()
    rvol = recent_vol / avg_vol_window
    
    # 3. Momentum (Returns)
    returns = norm_data.iloc[-1]
    
    # 4. Money Flow Score (MFS)
    # Si el retorno es (+) y RVOL es (>1), el dinero está entrando con fuerza.
    mfs = returns * rvol

    # Consolidación en Matrix
    stats_df = pd.DataFrame({
        "Ticker": returns.index,
        "Retorno %": returns.values,
        "RVOL (Intensidad)": rvol.values,
        "Money Flow Score": mfs.values
    }).set_index("Ticker").sort_values(by="Money Flow Score", ascending=False)

    # ─────────────────────────────────────────────
    # VISUALIZACIÓN: MAPA DE CALOR DE FLUJO REAL
    # ─────────────────────────────────────────────
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🚀 Matriz de Flujo Capital (Retorno vs Intensidad)")
        # Gráfico de burbujas: Eje X = Retorno, Eje Y = RVOL, Tamaño = MFS
        fig_flow = px.scatter(stats_df, x="Retorno %", y="RVOL (Intensidad)",
                            size=np.abs(stats_df["Money Flow Score"]),
                            color="Money Flow Score",
                            hover_name=stats_df.index,
                            color_continuous_scale="RdYlGn",
                            template="plotly_dark")
        fig_flow.add_hline(y=1.0, line_dash="dash", line_color="white", annotation_text="Media de Volumen")
        fig_flow.add_vline(x=0, line_dash="dash", line_color="white")
        st.plotly_chart(fig_flow, use_container_width=True)

    with col2:
        st.subheader("💎 Smart Money Top Picks")
        # Mostrar los 5 activos donde el volumen confirma la tendencia
        top_picks = stats_df.head(5)
        for ticker, row in top_picks.iterrows():
            st.markdown(f"""
            <div class="metric-box">
                <span style="font-size:1.2em; font-weight:bold;">{ticker}</span><br>
                <span style="color:#00FFAA;">MFS: {row['Money Flow Score']:.2f}</span> | 
                <span>RVOL: {row['RVOL (Intensidad)']:.2f}x</span>
            </div>
            """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # EVOLUCIÓN TEMPORAL
    # ─────────────────────────────────────────────
    st.subheader("📈 Convergencia de Tendencias")
    fig_perf = px.line(norm_data, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Plotly)
    fig_perf.update_layout(hovermode="x unified", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_perf, use_container_width=True)

    # Tabla Final con Formato Forense
    st.subheader("📊 Data Forensics: Flujo de Volumen")
    st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Money Flow Score']), use_container_width=True)

else:
    st.error("Error de Configuración: Seleccione al menos una categoría para ejecutar el SLY Engine.")
