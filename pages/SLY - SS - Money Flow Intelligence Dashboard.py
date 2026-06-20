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
</style>
""", unsafe_allow_html=True)

MARKETS = {
    "Sectores USA": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Global & Risk": ["SPY", "QQQ", "IWM", "EEM", "BTC-USD", "GLD"]
}

@st.cache_data(ttl=3600)
def get_data(tickers, start_date):
    try:
        df = yf.download(tickers, start=start_date, progress=False)
        if df.empty: return pd.DataFrame(), pd.DataFrame()
        # Limpieza de nulos inmediata
        return df['Close'].ffill().bfill(), df['Volume'].ffill().fillna(0)
    except:
        return pd.DataFrame(), pd.DataFrame()

# ─────────────────────────────────────────────
# LÓGICA DE PROCESAMIENTO
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
    
    if not close.empty and len(close) > 1:
        # --- CÁLCULOS CON FILTRO DE INTEGRIDAD ---
        # Evitamos división por cero o NaN en el primer registro
        first_valid_close = close.iloc[0].replace(0, np.nan)
        returns = ((close.iloc[-1] / first_valid_close) - 1) * 100
        
        # RVOL: Evitamos división por cero si el volumen medio es 0
        avg_vol = vol.mean().replace(0, np.nan)
        rvol = vol.iloc[-5:].mean() / avg_vol
        
        mfs = returns * rvol
        
        stats_df = pd.DataFrame({
            "Retorno %": returns,
            "RVOL (Intensidad)": rvol,
            "Money Flow Score": mfs
        })

        # PURGA DE DATOS CORRUPTOS (NaN e Infinitos)
        stats_df = stats_df.replace([np.inf, -np.inf], np.nan).dropna()
        stats_df = stats_df.sort_values(by="Money Flow Score", ascending=False)

        if not stats_df.empty:
            # ─────────────────────────────────────────────
            # VERDICTO AUTOMÁTICO
            # ─────────────────────────────────────────────
            st.subheader("🕵️ Veredicto Forense del Sistema")
            v_col1, v_col2 = st.columns(2)
            
            with v_col1:
                top_asset = stats_df.index[0]
                is_high_vol = stats_df.iloc[0]["RVOL (Intensidad)"] > 1.1
                verdict_top = f"Inyección masiva en <span class='highlight-green'>{top_asset}</span> confirmada por volumen." if is_high_vol else f"Subida técnica en <span class='highlight-green'>{top_asset}</span> con volumen bajo (Rally frágil)."
                st.markdown(f"<div class='report-card'><div class='verdict-title'>🚀 LIDER DE FLUJO</div><div class='verdict-text'>{verdict_top}</div></div>", unsafe_allow_html=True)

            with v_col2:
                worst_asset = stats_df.index[-1]
                is_dist = stats_df.iloc[-1]["RVOL (Intensidad)"] > 1.2
                verdict_worst = f"Distribución pesada en <span class='highlight-red'>{worst_asset}</span>. Salida de capital real." if is_dist else f"Debilidad en <span class='highlight-red'>{worst_asset}</span> por falta de interés."
                st.markdown(f"<div class='report-card'><div class='verdict-title'>⚠️ FUGA DE CAPITAL</div><div class='verdict-text'>{verdict_worst}</div></div>", unsafe_allow_html=True)

            # ─────────────────────────────────────────────
            # VISUALIZACIÓN (PARCHADA)
            # ─────────────────────────────────────────────
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.subheader("📍 Matriz Precio vs. Esfuerzo")
                # Aseguramos que el tamaño de burbuja sea siempre positivo y no nulo
                bubble_size = stats_df["Money Flow Score"].abs().fillna(0).clip(lower=5)
                
                fig = px.scatter(stats_df, x="Retorno %", y="RVOL (Intensidad)",
                                 size=bubble_size,
                                 color="Money Flow Score",
                                 text=stats_df.index,
                                 color_continuous_scale="RdYlGn",
                                 template="plotly_dark")
                
                fig.update_traces(textposition='top center', textfont_size=12)
                fig.update_layout(xaxis_title="Retorno %", yaxis_title="RVOL", plot_bgcolor='rgba(0,0,0,0)')
                fig.add_hline(y=1.0, line_dash="dash", line_color="#888")
                fig.add_vline(x=0, line_dash="dash", line_color="#888")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                st.subheader("📊 Ranking de Inyección")
                st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Money Flow Score']).format(precision=2), use_container_width=True)

            st.subheader("📈 Trayectoria de Capital")
            norm_line = (close[stats_df.index] / close[stats_df.index].iloc[0] - 1) * 100
            st.line_chart(norm_line)
        else:
            st.error("Error: Los datos procesados resultaron en valores nulos. Intente con otra ventana.")
    else:
        st.error("No se pudieron obtener datos suficientes para el período seleccionado.")
