import streamlit as st
import sys
import os
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE RUTAS (PARA QUE FUNCIONE EN PAGES/) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# --- IMPORTACIONES MODULARES ---
try:
    from data.data_provider import DataProvider
    from utils.formatting import format_currency, format_percent
except ImportError:
    st.error("No se encontraron las carpetas 'data' o 'utils' en la raíz. Asegúrate de que existan y tengan archivos __init__.py")
    st.stop()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Valuación Profesional FASE 1", layout="wide")

st.title("🔍 Análisis Fundamental - Fase 1")

# Sidebar
with st.sidebar:
    st.header("Entrada de Datos")
    ticker_input = st.text_input("Ticker de la empresa", value="ADBE").upper()
    btn_run = st.button("Analizar Ahora")

# Lógica Principal
if ticker_input:
    provider = DataProvider(ticker_input)
    
    with st.spinner(f"Cargando datos de {ticker_input}..."):
        success, error_msg = provider.fetch_all_data()
        
    if not success:
        st.error(error_msg)
    else:
        m = provider.get_main_metrics()
        
        # 1. Dashboard Superior (Tarjetas)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Precio Actual", f"{m['price']} {m['currency']}")
            st.caption(f"{m['name']}")
        with c2:
            st.metric("Market Cap", format_currency(m['market_cap'], m['currency']))
            st.caption(f"{m['industry']}")
        with c3:
            pe = f"{m['forward_pe']:.2f}" if m['forward_pe'] else "N/A"
            st.metric("Forward P/E", pe)
        with c4:
            st.metric("Beta (Volatilidad)", m['beta'] if m['beta'] else "N/A")

        st.divider()

        # 2. Gráficos Históricos
        summary = provider.get_financial_summary()
        
        if not summary.empty:
            st.subheader("Desempeño Histórico (Revenue vs Net Income)")
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=summary.index.strftime('%Y'), 
                y=summary['Revenue'], 
                name="Ingresos (Revenue)",
                marker_color='#1f77b4'
            ))
            if 'Net Income' in summary.columns:
                fig.add_trace(go.Scatter(
                    x=summary.index.strftime('%Y'), 
                    y=summary['Net Income'], 
                    name="Beneficio Neto",
                    line=dict(color='#ff7f0e', width=4)
                ))
            
            fig.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0),
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # 3. Tabla de datos crudos
            with st.expander("Ver tabla de datos financieros completa"):
                st.dataframe(summary.style.format(lambda x: format_currency(x, m['currency'])), use_container_width=True)
        else:
            st.warning("No hay suficientes datos históricos para graficar.")

# Pie de página técnico
st.sidebar.markdown("---")
st.sidebar.caption("Datos provistos por Yahoo Finance (yfinance)")
