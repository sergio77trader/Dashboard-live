import streamlit as st
from data.data_provider import DataProvider
from utils.formatting import format_currency, format_percent
import plotly.graph_objects as go

st.set_page_config(page_title="Investment Analyzer Pro", layout="wide")

st.title("🚀 Fundamental Stock Analyzer")

# Sidebar para entrada de datos
with st.sidebar:
    st.header("Configuración")
    ticker_input = st.text_input("Introduce Ticker (ej: ADBE, MSFT, GOOGL)", value="ADBE").upper()
    btn_analyze = st.button("Analizar Acción")

if btn_analyze or ticker_input:
    provider = DataProvider(ticker_input)
    
    with st.spinner(f"Obteniendo datos de {ticker_input}..."):
        success, error_msg = provider.fetch_all_data()
        
    if not success:
        st.error(error_msg)
    else:
        metrics = provider.get_main_metrics()
        
        # --- DASHBOARD SUPERIOR ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Precio Actual", f"{metrics['price']} {metrics['currency']}")
            st.caption(f"{metrics['name']} ({metrics['sector']})")
        with col2:
            st.metric("Market Cap", format_currency(metrics['market_cap'], metrics['currency']))
        with col3:
            st.metric("Forward P/E", f"{metrics['forward_pe']:.2f}" if metrics['forward_pe'] else "N/A")
        with col4:
            st.metric("Beta", f"{metrics['beta']:.2f}" if metrics['beta'] else "N/A")

        st.divider()

        # --- ANÁLISIS HISTÓRICO ---
        st.subheader("Evolución Financiera (Últimos años)")
        summary = provider.get_financial_summary()
        
        if not summary.empty:
            # Gráfico de Revenue y Net Income
            fig = go.Figure()
            fig.add_trace(go.Bar(x=summary.index, y=summary['Revenue'], name="Revenue"))
            if 'Net Income' in summary.columns:
                fig.add_trace(go.Scatter(x=summary.index, y=summary['Net Income'], name="Net Income", line=dict(color='orange', width=3)))
            
            fig.update_layout(title="Ingresos vs Beneficio Neto", barmode='group', height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Tabla de datos
            st.dataframe(summary.style.format(lambda x: format_currency(x, metrics['currency'])), use_container_width=True)
        else:
            st.warning("No se encontraron suficientes datos históricos.")

else:
    st.info("Introduce un ticker en la barra lateral para comenzar el análisis.")
