import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | ARBITRAGE V50")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.8rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #111; color: white; border-radius: 4px; }
    .stTabs [aria-selected="true"] { background-color: #00E676; color: black; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS: CURVA 2026 - 2027
# ─────────────────────────────────────────────
TICKERS_CONFIG = {
    # LECAPS (S) - Nombres probables en feed
    "S31M6": {"vto": date(2026, 3, 31), "payoff": 103.85},
    "S17A6": {"vto": date(2026, 4, 17), "payoff": 107.50},
    "S29Y6": {"vto": date(2026, 5, 29), "payoff": 111.65},
    "S30J6": {"vto": date(2026, 6, 30), "payoff": 115.40},
    "S31L6": {"vto": date(2026, 7, 31), "payoff": 119.55},
    "S31G6": {"vto": date(2026, 8, 31), "payoff": 124.10},
    "S30S6": {"vto": date(2026, 9, 30), "payoff": 128.45},
    "S30O6": {"vto": date(2026, 10, 30), "payoff": 132.85},
    "S30N6": {"vto": date(2026, 11, 30), "payoff": 137.45},
    "S30D6": {"vto": date(2026, 12, 30), "payoff": 142.25},
    # BONCAPS (T / TT)
    "TTM26": {"vto": date(2026, 3, 16), "payoff": 135.24},
    "TTJ26": {"vto": date(2026, 6, 30), "payoff": 144.63},
    "T30J6": {"vto": date(2026, 6, 30), "payoff": 144.90},
    "TTS26": {"vto": date(2026, 9, 15), "payoff": 152.10},
    "TTD26": {"vto": date(2026, 12, 15), "payoff": 161.14},
    "T15E7": {"vto": date(2027, 1, 15), "payoff": 165.80}
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS UNIVERSAL
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_raw_market_data():
    h = {'User-Agent': 'Mozilla/5.0'}
    endpoints = {
        "MEP": "https://data912.com/live/mep",
        "LETRAS": "https://data912.com/live/arg_letras",
        "NOTAS": "https://data912.com/live/arg_notes",
        "BONOS": "https://data912.com/live/arg_bonds"
    }
    
    collected_data = []
    mep_price = 1200.0 # Fallback
    
    for name, url in endpoints.items():
        try:
            r = requests.get(url, verify=False, timeout=10, headers=h)
            if r.status_code == 200:
                data = r.json()
                if name == "MEP":
                    mep_price = pd.DataFrame(data)['close'].median()
                else:
                    collected_data.extend(data)
        except:
            continue
            
    return mep_price, pd.DataFrame(collected_data)

def generate_matrix(mep, df):
    if df.empty: return pd.DataFrame()
    
    # NORMALIZACIÓN TOTAL
    df['symbol'] = df['symbol'].astype(str).str.replace(" ", "").str.upper()
    
    results = []
    today = date.today()

    for ticker, info in TICKERS_CONFIG.items():
        # Buscamos por coincidencia parcial para evitar errores de nombres largos
        match = df[df['symbol'].str.contains(ticker, na=False)]
        
        if not match.empty:
            price = float(match.iloc[0]['c'])
            days = (info['vto'] - today).days
            
            if days > 0 and price > 0:
                results.append({
                    "Ticker": ticker,
                    "Precio": price,
                    "Días": days,
                    "Payoff": info['payoff'],
                    "TEM": ((info['payoff'] / price) ** (30 / days) - 1),
                    "TEA": ((info['payoff'] / price) ** (365 / days) - 1),
                    "TNA": ((info['payoff'] / price) - 1) / days * 365,
                    "BREAKEVEN": mep * (info['payoff'] / price),
                    "BUFFER": ((mep * (info['payoff'] / price)) / mep) - 1
                })
    
    return pd.DataFrame(results).sort_values("Días")

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | CARRY TRADE V50")

# Botón de refresco con KEY única
if st.button("🔄 ACTUALIZAR TODO EL MERCADO", type="primary", key="btn_v50"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_raw_market_data()

if mep_now:
    st.metric("Dólar MEP Hoy", f"${mep_now:,.2f}")
    
    df_matrix = generate_matrix(mep_now, df_raw)
    
    # LAS 3 SOLAPAS + INSPECTOR
    t1, t2, t3, t4 = st.tabs(["📊 Matriz de Tasas", "🛡️ Breakeven MEP", "📈 Escenarios USD", "🔍 INSPECTOR DE MERCADO"])
    
    if not df_matrix.empty:
        with t1:
            st.subheader("Rendimiento Fijo en Pesos")
            st.dataframe(df_matrix[['Ticker', 'Precio', 'Días', 'TEM', 'TNA', 'TEA']].style.format({
                'TEM': '{:.2%}', 'TNA': '{:.2%}', 'TEA': '{:.2%}', 'Precio': '${:.2f}'
            }), use_container_width=True, height=500)

        with t2:
            st.subheader("Punto de Equilibrio (Breakeven)")
            fig = go.Figure()
            fig.add_hline(y=mep_now, line_dash="dash", line_color="red", annotation_text="Dólar Hoy")
            fig.add_trace(go.Scatter(x=df_matrix['Ticker'], y=df_matrix['BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_matrix['BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3)))
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_matrix[['Ticker', 'Precio', 'BREAKEVEN', 'BUFFER']].style.format({
                'BREAKEVEN': '${:.2f}', 'BUFFER': '{:.2%}', 'Precio': '${:.2f}'
            }), use_container_width=True)

        with t3:
            st.subheader("Retorno Neto en USD")
            scenarios = [0, 5, 10, 15, 20]
            sim = pd.DataFrame(index=df_matrix['Ticker'])
            for pct in scenarios:
                mep_fut = mep_now * (1 + pct/100)
                sim[f"Dólar +{pct}% (${mep_fut:.0f})"] = (df_matrix.set_index('Ticker')['Payoff'] / mep_fut) / (df_matrix.set_index('Ticker')['Precio'] / mep_now) - 1
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True, height=500)
            
    else:
        with t1: st.warning("No se encontraron coincidencias automáticas.")

    # PESTAÑA DE SEGURIDAD (Si los S no aparecen, aquí verás por qué)
    with t4:
        st.subheader("Datos crudos recibidos de la API")
        st.write("Si no ves las Lecaps arriba, buscá en esta tabla si el nombre 'symbol' es distinto al del código.")
        if not df_raw.empty:
            st.dataframe(df_raw[['symbol', 'c', 'v']], use_container_width=True)
        else:
            st.error("La API no devolvió ningún dato.")

else:
    st.error("Fallo de conexión total con los endpoints de mercado.")
