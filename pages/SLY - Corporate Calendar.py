import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import requests

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - SLY V3.0
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | EVENT TRACKER v3.0")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }
    h1 { color: #002D5A; font-weight: 800; border-bottom: 2px solid #004A99; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #DDD; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE SIGILO (ANTI-BOT)
# ─────────────────────────────────────────────
def get_stealth_session():
    session = requests.Session()
    # Simulamos un navegador real para que Yahoo no bloquee la IP del servidor
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

@st.cache_data(ttl=3600)
def fetch_events_v3(symbol_list):
    session = get_stealth_session()
    results = []
    
    # Barra de progreso para monitoreo
    prog = st.progress(0)
    status_text = st.empty()

    for idx, t in enumerate(symbol_list):
        try:
            status_text.text(f"Auditando: {t}")
            asset = yf.Ticker(t, session=session)
            
            # Extraemos del diccionario principal (más estable que .calendar)
            info = asset.info
            
            # 1. Obtener Próximo Balance
            # yfinance suele ponerlo en 'nextEarningsDate' o lo buscamos en earnings_dates
            next_earning_raw = info.get('nextEarningsDate') or 0
            if next_earning_raw > 0:
                next_earning_dt = datetime.fromtimestamp(next_earning_raw)
            else:
                # Fallback: intentar tabla de fechas
                e_df = asset.get_earnings_dates(limit=1)
                next_earning_dt = e_df.index[0] if e_df is not None and not e_df.empty else None

            # 2. Obtener Dividendos
            div_yield = info.get('dividendYield', 0)
            ex_div_raw = info.get('exDividendDate', 0)
            ex_div_dt = datetime.fromtimestamp(ex_div_raw) if ex_div_raw > 0 else None

            # 3. Calcular Días Restantes
            days_to = 999
            if next_earning_dt:
                # Normalizar para resta
                now = datetime.now()
                d_target = next_earning_dt.replace(tzinfo=None)
                days_to = (d_target - now).days

            results.append({
                "Activo": t,
                "Próximo Balance": next_earning_dt.strftime('%d/%m/%Y') if next_earning_dt else "S/D",
                "Días": days_to,
                "Ex-Dividendo": ex_div_dt.strftime('%d/%m/%Y') if ex_div_dt else "N/A",
                "Yield": f"{div_yield*100:.2f}%" if div_yield else "0.00%",
                "Precio Actual": f"${info.get('currentPrice', 0):.2f}"
            })
            
        except Exception as e:
            # En caso de error, dejamos constancia para el analista
            print(f"Error en {t}: {e}")
            continue
        prog.progress((idx+1)/len(symbol_list))

    status_text.empty()
    prog.empty()
    return pd.DataFrame(results)

# ─────────────────────────────────────────────
# INTERFAZ OPERATIVA
# ─────────────────────────────────────────────
st.title("🛡️ SLY - Terminal de Eventos Corporativos")

# Usamos pocos activos para el test de visibilidad inicial
TICKERS_TEST = "AAPL, NVDA, TSLA, MSFT, META, GGAL, YPF, PAMP"

input_tickers = st.text_area("Auditando activos (Separar por coma):", TICKERS_TEST)

if st.button("🚀 INICIAR ESCANEO DE EVENTOS"):
    t_list = [x.strip().upper() for x in input_tickers.split(",") if x.strip()]
    
    with st.spinner("Conectando con el Feed de Datos Global..."):
        df = fetch_events_v3(t_list)
    
    if not df.empty:
        # Lógica de color de grado institucional
        def style_risk(row):
            styles = [''] * len(row)
            d = row["Días"]
            if 0 <= d <= 5: # PELIGRO INMINENTE
                styles = ['background-color: #D32F2F; color: white; font-weight: bold;'] * len(row)
            elif 5 < d <= 15: # ADVERTENCIA
                styles = ['background-color: #FFF176; color: black;'] * len(row)
            return styles

        # Ordenar por cercanía del balance
        df_display = df.sort_values("Días", ascending=True)
        
        st.subheader("📅 Cronograma de Balances y Dividendos")
        st.dataframe(df_display.style.apply(style_risk, axis=1), use_container_width=True)
        
        st.success(f"Analizado con éxito: {len(df)} activos.")
    else:
        st.error("No se recibió información. Posible bloqueo de Yahoo o tickers mal escritos.")

st.info("SystemaTrader: v3.0 activa. Si el activo dice 'S/D' es porque aún no confirmó fecha oficial de balance.")
