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
    .report-box { 
        background-color: #111; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #00E676;
        margin-bottom: 25px;
    }
    .insight-title { color: #00E676; font-weight: bold; font-size: 1.2em; }
</style>
""", unsafe_allow_html=True)

# DICCIONARIO MAESTRO DE ACTIVOS
MARKETS = {
    "Metales": ["GLD", "SLV", "CPER", "PPLT"],
    "Sectores S&P500": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Crypto (Proxy)": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Internacionales": ["SPY", "QQQ", "EEM", "EWZ", "FXI", "ARKK"],
    "Macro Drivers": ["DX-Y.NYB", "TLT", "USO", "VNQ", "HYG"]
}

@st.cache_data(ttl=3600)
def get_market_data(tickers, start_date):
    # Ajuste de ticker para DXY si es necesario
    data = yf.download(tickers, start=start_date, progress=False)['Close']
    if isinstance(data, pd.Series): # Caso de un solo ticker
        data = data.to_frame()
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
    raw_data = raw_data.ffill() # Limpieza de datos
    
    # NORMALIZACIÓN
    norm_data = (raw_data / raw_data.iloc[0] - 1) * 100

    # ─────────────────────────────────────────────
    # MOTOR DE EXPLICACIONES (SYSTEMATRADER LOGIC)
    # ─────────────────────────────────────────────
    last_perf = norm_data.iloc[-1].sort_values(ascending=False)
    top_asset = last_perf.index[0]
    bot_asset = last_perf.index[-1]
    avg_perf = last_perf.mean()
    
    # Análisis de Contexto Temporal
    context_msg = ""
    if lookback == "Último Mes":
        context_msg = "Análisis de **Momentum Táctico**. Los flujos reflejan volatilidad de corto plazo y posicionamiento especulativo."
    elif lookback == "Últimos 6 Meses":
        context_msg = "Análisis de **Ciclo Intermedio**. Se observa la rotación de sectores y la respuesta a las tasas de interés."
    elif lookback == "YTD (Año actual)":
        context_msg = f"Análisis de **Narrativa Anual {today.year}**. Rendimiento acumulado desde la apertura de enero."
    else:
        context_msg = "Análisis de **Tendencia Estructural**. Refleja cambios de largo plazo en el régimen macroeconómico."

    # Análisis de Correlación DXY (si existe)
    dxy_correlation = ""
    if "DX-Y.NYB" in all_selected_tickers:
        dxy_perf = last_perf["DX-Y.NYB"]
        if dxy_perf > 0 and avg_perf < 0:
            dxy_correlation = "⚠️ **Divergencia Detectada:** La fortaleza del DXY está asfixiando los activos de riesgo (Risk-Off)."
        elif dxy_perf < 0 and avg_perf > 0:
            dxy_correlation = "✅ **Viento a Favor:** La debilidad global del dólar está impulsando el rally en commodities y acciones."

    # Renderizado del Cuadro de Inteligencia
    st.markdown(f"""
    <div class="report-box">
        <span class="insight-title">🎙️ Veredicto del Sistema (Ventana: {lookback})</span><br>
        <p>{context_msg}</p>
        <ul>
            <li><b>Líder del Periodo:</b> {top_asset} con un retorno de <span style="color:#00E676">{last_perf[top_asset]:+.2f}%</span>.</li>
            <li><b>Rezagado del Periodo:</b> {bot_asset} con una caída de <span style="color:#FF5252">{last_perf[bot_asset]:.2f}%</span>.</li>
            <li><b>Sesgo del Mercado:</b> {'Alcista' if avg_perf > 0 else 'Bajista'} (Promedio: {avg_perf:+.2f}%).</li>
        </ul>
        {dxy_correlation}
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # VISUAL 1: EL GRÁFICO DE CARRERA
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
    # VISUAL 2: RANKING Y VOLATILIDAD
    # ─────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🏆 Ranking de Fuerza")
        fig_bar = px.bar(last_perf, 
                         orientation='h', 
                         labels={"value": "Retorno %", "index": "Activo"},
                         color=last_perf,
                         color_continuous_scale="RdYlGn",
                         template="plotly_dark")
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📊 Resumen de Volatilidad")
        volatility = raw_data.pct_change().std() * (252**0.5) * 100
        st.dataframe(volatility.rename("Volatilidad Anualizada %").sort_values(ascending=False), use_container_width=True)

else:
    st.warning("Seleccione al menos una categoría en la barra lateral para procesar los vectores de datos.")
