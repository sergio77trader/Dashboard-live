import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | EVENT TRACKER v2.0")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #00E676; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    .status-panel { padding: 10px; border-radius: 5px; background-color: #E8F5E9; color: #2E7D32; font-weight: bold; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# Lista Maestra reducida para el test inicial
DEFAULT_TICKERS = 'AAPL, NVDA, MSFT, TSLA, GGAL, YPF, MELI, META, AMZN, KO, JPM'

# ─────────────────────────────────────────────
# MOTOR DE EXTRACCIÓN v2.0 (HISTORICAL ANALYSIS)
# ─────────────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_robust_events(symbol_list):
    results = []
    prog = st.progress(0)
    
    for idx, t in enumerate(symbol_list):
        try:
            asset = yf.Ticker(t)
            
            # 1. BÚSQUEDA DE BALANCE (EARNINGS)
            # Intentamos obtener la tabla de fechas de ganancias
            earnings_df = asset.get_earnings_dates(limit=5)
            next_earning = "S/D"
            days_to_earn = 999
            
            if earnings_df is not None and not earnings_df.empty:
                # Las fechas futuras suelen tener el campo 'Reported EPS' vacío
                future_dates = earnings_df[earnings_df.index > datetime.now(earnings_df.index.tz)]
                if not future_dates.empty:
                    date_obj = future_dates.index[0]
                    next_earning = date_obj.strftime('%d/%m/%Y')
                    days_to_earn = (date_obj.replace(tzinfo=None) - datetime.now()).days
                else:
                    # Si no hay fecha confirmada, Yahoo a veces la pone en .calendar
                    cal = asset.calendar
                    date_cal = cal.get('Earnings Date', [None])[0] if isinstance(cal, dict) else None
                    if date_cal:
                        next_earning = date_cal.strftime('%d/%m/%Y')
                        days_to_earn = (date_cal.replace(tzinfo=None) - datetime.now()).days

            # 2. BÚSQUEDA DE DIVIDENDOS
            # En lugar de .info, miramos el historial real de pagos
            div_history = asset.dividends
            last_div_date = "No paga"
            div_yield = "0.00%"
            
            if not div_history.empty:
                last_div_date = div_history.index[-1].strftime('%d/%m/%Y')
                # Intentamos sacar el Yield del info
                try:
                    yield_val = asset.info.get('dividendYield')
                    if yield_val: div_yield = f"{yield_val*100:.2f}%"
                except: pass

            results.append({
                "Activo": t,
                "Próximo Balance": next_earning,
                "Días restantes": days_to_earn,
                "Último Dividendo": last_div_date,
                "Div. Yield": div_yield
            })
            time.sleep(0.2) # Jitter para evitar baneo
        except Exception as e:
            continue
        prog.progress((idx+1)/len(symbol_list))
    
    prog.empty()
    return pd.DataFrame(results)

# ─────────────────────────────────────────────
# INTERFAZ DE USUARIO
# ─────────────────────────────────────────────
st.title("🛡️ SLY - Calendario de Eventos v2.0")
st.markdown('<div class="status-panel">Motor de Análisis Histórico Activo: Detectando fechas ocultas.</div>', unsafe_allow_html=True)

input_tickers = st.text_area("Ingresa los activos para auditar:", DEFAULT_TICKERS)
filter_days = st.slider("Rango de búsqueda (días):", 1, 120, 90)

if st.button("🚀 AUDITAR MERCADO"):
    t_list = [x.strip().upper() for x in input_tickers.split(",") if x.strip()]
    df = fetch_robust_events(t_list)
    
    if not df.empty:
        # Lógica de color para riesgo
        def style_logic(row):
            styles = [''] * len(row)
            d = row["Días restantes"]
            if 0 <= d <= 5: # EMERGENCIA: Balance en menos de 5 días
                styles = ['background-color: #FF5252; color: white; font-weight: bold;'] * len(row)
            elif 5 < d <= 15: # ADVERTENCIA: Balance en menos de 15 días
                styles = ['background-color: #FFF9C4; color: #333;'] * len(row)
            return styles

        # Ordenar por cercanía
        df_final = df.sort_values("Días restantes", ascending=True)
        
        # Ocultar la columna de cálculo interna "Días restantes" para limpieza visual
        st.dataframe(df_final.style.apply(style_logic, axis=1), use_container_width=True)
        
        st.success(f"Análisis completado para {len(df)} activos.")
    else:
        st.error("No se pudo extraer información. Yahoo Finance podría estar limitando las peticiones.")

st.info("Nota técnica: Si un activo dice 'S/D' es porque la empresa aún no ha reportado su cronograma a la bolsa de valores.")
