import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE INTERFAZ
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | CORPORATE CALENDAR")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }
    h1 { color: #0D47A1; font-weight: 800; border-bottom: 3px solid #1E88E5; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    .event-card { padding: 15px; border-radius: 10px; background: white; border-left: 5px solid #1E88E5; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# Lista Maestra (Importada de tu Matrix o simplificada aquí para el ejemplo)
# Puedes usar la misma variable MASTER_TICKERS de tu otro script
TICKERS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'GGAL', 'YPF', 'MELI', 'GLOB']

# ─────────────────────────────────────────────
# MOTOR DE BÚSQUEDA DE EVENTOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=86400) # Cache por 24 horas (Los eventos no cambian cada minuto)
def fetch_corporate_events(symbol_list):
    results = []
    prog = st.progress(0)
    status_text = st.empty()

    for idx, t in enumerate(symbol_list):
        try:
            status_text.text(f"Consultando Calendario: {t}")
            asset = yf.Ticker(t)
            
            # 1. Obtener Fecha de Balance (Earnings)
            cal = asset.calendar
            # yfinance devuelve un dict o df según la versión
            if isinstance(cal, pd.DataFrame):
                earnings_date = cal.loc['Earnings Date'].iloc[0]
            else:
                earnings_date = cal.get('Earnings Date', [None])[0]

            # 2. Obtener Fecha de Ex-Dividendo
            info = asset.info
            ex_div_date = info.get('exDividendDate')
            if ex_div_date:
                ex_div_date = datetime.fromtimestamp(ex_div_date)
            
            # 3. Calcular Días para el Balance
            days_to_earnings = None
            if earnings_date:
                # Normalizar fechas para resta
                d1 = earnings_date.replace(tzinfo=None) if hasattr(earnings_date, 'replace') else earnings_date
                days_to_earnings = (d1 - datetime.now()).days

            results.append({
                "Activo": t,
                "Próximo Balance": earnings_date.strftime('%d/%m/%Y') if earnings_date else "S/D",
                "Días restantes": days_to_earnings if days_to_earnings is not None else 999,
                "Ex-Dividendo": ex_div_date.strftime('%d/%m/%Y') if ex_div_date else "No paga",
                "Dividend Yield": f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "0.00%"
            })
            time.sleep(0.1) # Evitar bloqueo de IP
        except:
            continue
        prog.progress((idx+1)/len(symbol_list))
    
    status_text.empty()
    prog.empty()
    return pd.DataFrame(results)

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
st.title("🛡️ SLY - Calendario Institucional de Eventos")

col_filter1, col_filter2 = st.columns([2,1])
with col_filter1:
    search_list = st.text_area("Lista de Vigilancia (separar por comas):", ", ".join(TICKERS))
with col_filter2:
    filter_days = st.slider("Ver balances en los próximos (días):", 1, 90, 30)

if st.button("🚀 ACTUALIZAR CALENDARIO"):
    target_list = [x.strip().upper() for x in search_list.split(",")]
    df_events = fetch_corporate_events(target_list)
    
    if not df_events.empty:
        # Filtrar por días de riesgo
        df_filtered = df_events[df_events["Días restantes"] <= filter_days].sort_values("Días restantes")
        
        st.subheader(f"📅 Eventos detectados para los próximos {filter_days} días")
        
        # Estilo de Alerta de Riesgo
        def style_risk(row):
            styles = [''] * len(row)
            # Si el balance es en menos de 7 días: ALERTA CRÍTICA
            if 0 <= row["Días restantes"] <= 7:
                styles = ['background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'] * len(row)
            # Si el balance es hoy o mañana: FLASH
            if 0 <= row["Días restantes"] <= 2:
                styles = ['background-color: #D50000; color: white; font-weight: bold;'] * len(row)
            return styles

        try:
            st.dataframe(df_filtered.style.apply(style_risk, axis=1), use_container_width=True)
        except:
            st.dataframe(df_filtered, use_container_width=True)
            
        st.success("SystemaTrader: Calendario sincronizado con éxito.")
    else:
        st.warning("No se encontraron eventos próximos para estos activos.")

st.divider()
with st.expander("📘 Manual de Operativa de Eventos"):
    st.markdown("""
    *   **Balances (Earnings):** Un activo suele moverse +/- 5% tras el balance. **REGLA SLY:** No abrir nuevas posiciones 48hs antes del evento.
    *   **Ex-Dividendo:** Es el último día para comprar y cobrar. Al día siguiente, la acción suele bajar el valor del dividendo. No es una caída "real", es un ajuste técnico.
    *   **S/D (Sin Datos):** Significa que la empresa aún no ha confirmado la fecha oficial del próximo reporte.
    """)
