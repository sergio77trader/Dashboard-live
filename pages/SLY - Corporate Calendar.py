import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - SLY V4.0
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | DIVIDENDOS Y BALANCES")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1a237e; font-weight: 800; border-bottom: 2px solid #1a237e; }
    .stDataFrame { background-color: white; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

@st.cache_data(ttl=3600)
def fetch_corporate_data(symbol_list):
    session = get_session()
    results = []
    prog = st.progress(0)
    
    for idx, t in enumerate(symbol_list):
        try:
            asset = yf.Ticker(t, session=session)
            
            # 1. CAPTURA DE BALANCE (EARNINGS)
            # Usamos get_earnings_dates que es más profundo que .calendar
            e_df = asset.get_earnings_dates(limit=10)
            next_balance = "No confirmada"
            if e_df is not None and not e_df.empty:
                # Buscamos la primera fecha que sea mayor a hoy
                future_earnings = e_df[e_df.index > datetime.now(e_df.index.tz)]
                if not future_earnings.empty:
                    next_balance = future_earnings.index[0].strftime('%d/%m/%Y')

            # 2. CAPTURA DE DIVIDENDOS (PAGOS)
            divs = asset.dividends
            last_payment = "N/A"
            est_next_payment = "Analizando..."
            
            if not divs.empty:
                # Última fecha de pago registrada
                last_payment_dt = divs.index[-1]
                last_payment = last_payment_dt.strftime('%d/%m/%Y')
                
                # Estimación Institucional:
                # Si pagó hace 3 meses (trimestral), sumamos 90 días
                # Si pagó hace 1 año (anual), sumamos 365 días
                if len(divs) > 1:
                    delta = divs.index[-1] - divs.index[-2]
                    est_date = last_payment_dt + delta
                    est_next_payment = est_date.strftime('%d/%m/%Y')
                else:
                    est_next_payment = (last_payment_dt + timedelta(days=90)).strftime('%d/%m/%Y')

            # 3. INFO GENERAL
            price = asset.info.get('currentPrice', 0)
            name = asset.info.get('longName', t)

            results.append({
                "Ticker": t,
                "Empresa": name[:25],
                "Próximo Balance": next_balance,
                "Último Pago Div": last_payment,
                "PRÓXIMO PAGO (EST)": est_next_payment,
                "Precio": f"${price:.2f}"
            })
            
        except Exception as e:
            continue
        prog.progress((idx+1)/len(symbol_list))

    prog.empty()
    return pd.DataFrame(results)

# ─────────────────────────────────────────────
# INTERFAZ Streamlit
# ─────────────────────────────────────────────
st.title("🛡️ SLY - Calendario de Pagos y Balances")
st.write("Auditoría de fechas de cobro y reportes trimestrales.")

# Lista de tickers sugerida
TICKERS_INPUT = "AAPL, NVDA, KO, MCD, GGAL, YPF, XOM, MSFT, JPM"

target_tickers = st.text_area("Ingresa Tickers (separados por coma):", TICKERS_INPUT)

if st.button("🚀 GENERAR CALENDARIO"):
    t_list = [x.strip().upper() for x in target_tickers.split(",") if x.strip()]
    
    with st.spinner("Rastreando historial de pagos y reportes..."):
        df = fetch_corporate_data(t_list)
    
    if not df.empty:
        st.subheader("📋 Resultados de la Auditoría")
        
        # Estilo para destacar pagos próximos
        def highlight_soon(val):
            return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;' if '2024' in str(val) else ''

        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.success("Análisis completado. Las fechas estimadas se basan en el comportamiento histórico de la empresa.")
        
        st.info("""
        **Nota Institucional:** 
        * **Próximo Pago (EST):** Es la fecha calculada por el sistema según el ciclo previo (Trimestral/Semestral).
        * **Próximo Balance:** Fecha en la que la empresa anuncia ganancias. Si dice 'No confirmada', Yahoo aún no recibió el reporte oficial.
        """)
    else:
        st.error("Error: No se pudo obtener información. Verifica los tickers.")

st.warning("⚠️ Los datos de dividendos en Cedears/ADRs pueden tener un lag de 48-72hs respecto a la bolsa de origen.")
