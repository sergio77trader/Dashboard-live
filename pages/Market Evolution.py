import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE TERMINAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | GLOBAL MACRO")

st.markdown("""
<style>
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stSelectbox label { color: #00E676; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# DICCIONARIO MAESTRO DE ACTIVOS
MARKETS = {
    "Metales": ["GLD", "SLV", "CPER", "PPLT"],
    "Sectores S&P500": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Crypto (Proxy)": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Internacionales": ["SPY", "QQQ", "EEM", "EWZ", "FXI", "ARKK"],
    "Macro Drivers": ["DXY", "TLT", "USO", "VNQ", "HYG"]
}

# ─────────────────────────────────────────────
# MOTOR DE EXTRACCIÓN
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_market_data(tickers, start_date):
    data = yf.download(tickers, start=start_date, progress=False)['Close']
    return data

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🌐 EVOLUCIÓN DE MERCADOS GLOBALES")

with st.sidebar:
    st.header("⚙️ Filtros de Análisis")
    lookback = st.selectbox("Ventana de Tiempo:", 
                            ["Último Mes", "Últimos 6 Meses", "YTD (Año actual)", "Último Año", "Máximo Histórico"],
                            index=2)
    
    # Mapeo de fechas
    today = datetime.now()
    if lookback == "Último Mes": start = today - timedelta(days=30)
    elif lookback == "Últimos 6 Meses": start = today - timedelta(days=180)
    elif lookback == "YTD (Año actual)": start = datetime(today.year, 1, 1)
    elif lookback == "Último Año": start = today - timedelta(days=365)
    else: start = datetime(2010, 1, 1)

    selected_cat = st.multiselect("Seleccionar Mercados:", 
                                  options=list(MARKETS.keys()), 
                                  default=["Metales", "Crypto (Proxy)", "Macro Drivers"])

# PROCESAMIENTO
all_selected_tickers = []
for cat in selected_cat:
    all_selected_tickers.extend(MARKETS[cat])

if all_selected_tickers:
    raw_data = get_market_data(all_selected_tickers, start)
    
    # NORMALIZACIÓN (Base 100 / Rendimiento %)
    # Calculamos la variación porcentual desde el primer día del rango
    norm_data = (raw_data / raw_data.iloc[0] - 1) * 100

    # ─────────────────────────────────────────────
    # VISUAL 1: EL GRÁFICO DE CARRERA (PERFORMANCE)
    # ─────────────────────────────────────────────
    st.subheader("🚀 Rendimiento Relativo (%) - Comparativa Normalizada")
    
    fig_perf = px.line(norm_data, 
                       labels={"value": "Variación %", "Date": "Fecha"},
                       template="plotly_dark",
                       color_discrete_sequence=px.colors.qualitative.Plotly)
    
    fig_perf.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    # ─────────────────────────────────────────────
    # VISUAL 2: RANKING DE FUERZA (BARRAS)
    # ─────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🏆 Ranking de Fuerza")
        last_perf = norm_data.iloc[-1].sort_values(ascending=False)
        fig_bar = px.bar(last_perf, 
                         orientation='h', 
                         labels={"value": "Retorno %", "index": "Activo"},
                         color=last_perf,
                         color_continuous_scale="RdYlGn",
                         template="plotly_dark")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # Aquí pondremos la Matriz de Correlación en la siguiente versión
        st.subheader("📊 Resumen de Volatilidad")
        volatility = raw_data.pct_change().std() * (252**0.5) * 100 # Anualizada
        st.dataframe(volatility.rename("Volatilidad Anualizada %").sort_values(ascending=False), use_container_width=True)

else:
    st.warning("Seleccione al menos una categoría en la barra lateral para procesar los datos.")
