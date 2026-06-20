import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MONEY FLOW ENGINE", page_icon="🏦")

# CSS para Legibilidad Extrema
st.markdown("""
<style>
    .stApp { background-color: #0B0E11; color: #EAECEF; }
    .report-card { 
        background-color: #1E2329; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 6px solid #F0B90B;
        margin-bottom: 15px;
    }
    .verdict-title { color: #F0B90B; font-weight: bold; font-size: 1.4em; margin-bottom: 10px; }
    .verdict-text { color: #EAECEF; font-size: 1.1em; line-height: 1.5; }
    .highlight-green { color: #00FFAA; font-weight: bold; }
    .highlight-red { color: #FF3B30; font-weight: bold; }
    .highlight-yellow { color: #FFCC00; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

MARKETS = {
    "Sectores USA": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Global & Risk": ["SPY", "QQQ", "IWM", "EEM", "BTC-USD", "GLD"]
}

@st.cache_data(ttl=3600)
def get_data(tickers, start_date):
    df = yf.download(tickers, start=start_date, progress=False)
    return df['Close'].ffill(), df['Volume'].ffill()

# ─────────────────────────────────────────────
# LÓGICA DE CONTROL
# ─────────────────────────────────────────────
st.title("🏦 SLY MONEY FLOW INTELLIGENCE")

with st.sidebar:
    st.header("⚙️ CONFIG")
    lookback = st.selectbox("Ventana:", ["1 Mes", "3 Meses", "6 Meses", "YTD"], index=0)
    today = datetime.now()
    dates = {"1 Mes": 30, "3 Meses": 90, "6 Meses": 180, "YTD": (today - datetime(today.year, 1, 1)).days}
    start = today - timedelta(days=dates[lookback])
    selected_cat = st.multiselect("Filtros:", list(MARKETS.keys()), default="Sectores USA")

all_tickers = []
for cat in selected_cat: all_tickers.extend(MARKETS[cat])

if all_tickers:
    close, vol = get_data(all_tickers, start)
    
    # Cálculos Forenses
    returns = ((close.iloc[-1] / close.iloc[0]) - 1) * 100
    rvol = vol.iloc[-5:].mean() / vol.mean()
    mfs = returns * rvol
    
    stats_df = pd.DataFrame({
        "Retorno %": returns,
        "RVOL (Intensidad)": rvol,
        "Money Flow Score": mfs
    }).sort_values(by="Money Flow Score", ascending=False)

    # ─────────────────────────────────────────────
    # MÓDULO DE INTERPRETACIÓN AUTOMÁTICA (EL VERDICTO)
    # ─────────────────────────────────────────────
    st.subheader("🕵️ Veredicto Forense del Sistema")
    
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        # Detectar Inyección Institucional
        top_asset = stats_df.index[0]
        if stats_df.iloc[0]["RVOL (Intensidad)"] > 1.1:
            verdict_top = f"El capital está fluyendo agresivamente hacia <span class='highlight-green'>{top_asset}</span>. El volumen confirma que las instituciones están comprando la tendencia."
        else:
            verdict_top = f"<span class='highlight-green'>{top_asset}</span> lidera en precio, pero el volumen es bajo. Es un rally de 'escasez de vendedores', cuidado con la falta de liquidez."
            
        st.markdown(f"""<div class="report-card">
            <div class="verdict-title">🚀 LÍDER DE FLUJO REAL</div>
            <div class="verdict-text">{verdict_top}</div>
        </div>""", unsafe_allow_html=True)

    with col_v2:
        # Detectar Fuga o Distribución
        worst_asset = stats_df.index[-1]
        if stats_df.iloc[-1]["RVOL (Intensidad)"] > 1.2:
            verdict_worst = f"ALERTA: <span class='highlight-red'>{worst_asset}</span> está bajo <b>Distribución Institucional</b>. El volumen alto en la caída confirma salida masiva de capital."
        else:
            verdict_worst = f"<span class='highlight-red'>{worst_asset}</span> está cayendo con volumen bajo. Podría ser un retroceso técnico saludable o falta de interés temporal."

        st.markdown(f"""<div class="report-card">
            <div class="verdict-title">⚠️ FUGA DE CAPITAL</div>
            <div class="verdict-text">{verdict_worst}</div>
        </div>""", unsafe_allow_html=True)

    # Análisis de Rotación Especial
    st.info(f"**ANÁLISIS DE ROTACIÓN:** El sector **{stats_df.index[0]}** presenta la mayor eficiencia de capital, mientras que el mercado está castigando severamente a **{stats_df.index[-1]}**.")

    # ─────────────────────────────────────────────
    # VISUALIZACIÓN MEJORADA
    # ─────────────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📍 Matriz Precio vs. Esfuerzo")
        fig = px.scatter(stats_df, x="Retorno %", y="RVOL (Intensidad)",
                         size=np.abs(stats_df["Money Flow Score"]).clip(lower=5),
                         color="Money Flow Score",
                         text=stats_df.index,
                         color_continuous_scale="RdYlGn",
                         template="plotly_dark")
        
        # Ajustes de legibilidad en el gráfico
        fig.update_traces(textposition='top center', textfont_size=12)
        fig.update_layout(
            xaxis_title="Retorno Nominal (%)",
            yaxis_title="Intensidad de Volumen (RVOL)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.add_hline(y=1.0, line_dash="dash", line_color="#888")
        fig.add_vline(x=0, line_dash="dash", line_color="#888")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("📊 Ranking de Inyección")
        st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Money Flow Score'])
                     .format(precision=2), use_container_width=True, height=450)

    # Gráfico de Líneas con mejor contraste
    st.subheader("📈 Trayectoria de Capital")
    norm_line = (close / close.iloc[0] - 1) * 100
    fig_line = px.line(norm_line, template="plotly_dark")
    fig_line.update_layout(
        yaxis_title="Rendimiento Relativo %",
        legend_title="Activos",
        hovermode="x unified"
    )
    st.plotly_chart(fig_line, use_container_width=True)

else:
    st.warning("Seleccione activos para iniciar el motor.")
