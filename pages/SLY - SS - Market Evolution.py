import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE TERMINAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | GLOBAL MACRO LIGHT")

# CSS para forzar tema blanco y legibilidad
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    h1, h2, h3 { color: #004D40; font-weight: 800; }
    .report-box { 
        background-color: #F8F9FA; 
        padding: 25px; 
        border-radius: 12px; 
        border: 1px solid #E0E0E0;
        margin-bottom: 25px;
        color: #1C1E21;
    }
    .insight-title { color: #2E7D32; font-weight: bold; font-size: 1.3em; }
    .stDataFrame { background-color: white; }
</style>
""", unsafe_allow_html=True)

# DICCIONARIO MAESTRO
MARKETS = {
    "Metales": ["GLD", "SLV", "CPER", "PPLT"],
    "Sectores S&P500": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Crypto (Proxy)": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Internacionales": ["SPY", "QQQ", "EEM", "EWZ", "FXI", "ARKK"],
    "Macro Drivers": ["DX-Y.NYB", "TLT", "USO", "VNQ", "HYG"]
}

@st.cache_data(ttl=3600)
def get_market_data(tickers, start_date):
    data = yf.download(tickers, start=start_date, progress=False)['Close']
    if isinstance(data, pd.Series): data = data.to_frame()
    return data.ffill()

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
st.title("🌐 EVOLUCIÓN DE MERCADOS GLOBALES")

with st.sidebar:
    st.header("⚙️ Configuración")
    lookback = st.selectbox("Ventana de Tiempo:", 
                            ["Último Mes", "Últimos 6 Meses", "YTD (Año actual)", "Último Año", "Máximo Histórico"],
                            index=2)
    
    today = datetime.now()
    if lookback == "Último Mes": start = today - timedelta(days=30)
    elif lookback == "Últimos 6 Meses": start = today - timedelta(days=180)
    elif lookback == "YTD (Año actual)": start = datetime(today.year, 1, 1)
    elif lookback == "Último Año": start = today - timedelta(days=365)
    else: start = datetime(2010, 1, 1)

    selected_cat = st.multiselect("Categorías:", options=list(MARKETS.keys()), 
                                  default=["Metales", "Internacionales", "Macro Drivers"])

# PROCESAMIENTO
all_selected_tickers = []
for cat in selected_cat:
    all_selected_tickers.extend(MARKETS[cat])

if all_selected_tickers:
    raw_data = get_market_data(all_selected_tickers, start)
    norm_data = (raw_data / raw_data.iloc[0] - 1) * 100

    # ─────────────────────────────────────────────
    # MOTOR DE MÉTRICAS DETALLADAS (FORENSICS)
    # ─────────────────────────────────────────────
    returns = norm_data.iloc[-1]
    vols = raw_data.pct_change().std() * (252**0.5) * 100
    
    # Cálculo de Max Drawdown
    roll_max = raw_data.cummax()
    drawdowns = (raw_data - roll_max) / roll_max * 100
    max_dd = drawdowns.min()

    # Consolidación
    stats_df = pd.DataFrame({
        "Retorno %": returns,
        "Volatilidad %": vols,
        "Eficiencia (Ret/Vol)": returns / vols,
        "Max Drawdown %": max_dd
    }).sort_values(by="Retorno %", ascending=False)

    # ─────────────────────────────────────────────
    # EXPLICACIONES DETALLADAS
    # ─────────────────────────────────────────────
    top_ticker = stats_df.index[0]
    eff_ticker = stats_df["Eficiencia (Ret/Vol)"].idxmax()
    
    st.markdown(f"""
    <div class="report-box">
        <span class="insight-title">🎙️ Veredicto del Sistema (Ventana: {lookback})</span><br>
        <p>El mercado presenta un régimen de <b>{'Apetito por Riesgo' if returns.mean() > 0 else 'Aversión al Riesgo'}</b>.</p>
        <ul>
            <li><b>Líder Nominal:</b> {top_ticker} ha dominado el tablero con un {returns[top_ticker]:+.2f}%.</li>
            <li><b>Líder de Eficiencia:</b> {eff_ticker} es el activo con mejor relación riesgo-beneficio. Su subida ha sido más constante y menos errática.</li>
            <li><b>Riesgo Crítico:</b> {stats_df['Max Drawdown %'].idxmin()} registró la mayor caída ({stats_df['Max Drawdown %'].min():.2f}%), indicando una zona de alta volatilidad estructural.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # GRÁFICO LÍNEAS (WHITE TEMPLATE)
    # ─────────────────────────────────────────────
    st.subheader("🚀 Rendimiento Relativo (%) - Comparativa Normalizada")
    fig_perf = px.line(norm_data, template="plotly_white")
    fig_perf.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    # ─────────────────────────────────────────────
    # TABLAS Y RANKINGS
    # ─────────────────────────────────────────────
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("🏆 Ranking de Fuerza")
        fig_bar = px.bar(returns.sort_values(), orientation='h', template="plotly_white",
                         color=returns.sort_values(), color_continuous_scale="RdYlGn")
        fig_bar.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.subheader("📊 Ficha Técnica de Activos")
        st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Eficiencia (Ret/Vol)']), 
                     use_container_width=True, height=400)

else:
    st.warning("Seleccione categorías para iniciar el análisis.")
