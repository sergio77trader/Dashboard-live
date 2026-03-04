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

st.set_page_config(layout="wide", page_title="SYSTEMATRADER | ARBITRAGE MASTER")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.85rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    h3 { color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS: CURVA 2026 - 2027
# ─────────────────────────────────────────────
TICKERS_DATE = {
    # LECAPS (S)
    "S31M6": date(2026, 3, 31), "S17A6": date(2026, 4, 17), "S29Y6": date(2026, 5, 29),
    "S30J6": date(2026, 6, 30), "S31L6": date(2026, 7, 31), "S31G6": date(2026, 8, 31),
    "S30S6": date(2026, 9, 30), "S30O6": date(2026, 10, 30), "S30N6": date(2026, 11, 30),
    "S30D6": date(2026, 12, 30),
    # BONCAPS (T / TT)
    "TTM26": date(2026, 3, 16), "TTJ26": date(2026, 6, 30), "T30J6": date(2026, 6, 30),
    "TTS26": date(2026, 9, 15), "TTD26": date(2026, 12, 15), "T15E7": date(2027, 1, 15),
    "T15M7": date(2027, 3, 15), "T15J7": date(2027, 6, 15)
}

PAYOFF = {
    "S31M6": 103.50, "S17A6": 107.20, "S29Y6": 111.40, "S30J6": 115.10,
    "S31L6": 119.30, "S31G6": 123.80, "S30S6": 128.20, "S30O6": 132.50,
    "S30N6": 137.10, "S30D6": 142.00, "TTM26": 135.24, "TTJ26": 144.63,
    "T30J6": 144.90, "TTS26": 152.10, "TTD26": 161.14, "T15E7": 165.80,
    "T15M7": 172.30, "T15J7": 181.50
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (DATA912 BRIDGE)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_market_data():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=h).json()
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=h).json()
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=h).json()
        
        mep = pd.DataFrame(r_mep)['close'].median()
        df_full = pd.DataFrame(r_notes + r_bonds)
        return mep, df_full
    except Exception as e:
        st.error(f"Falla de conexión: {e}")
        return None, None

def calculate_arbitrage_metrics(mep, df):
    if df.empty or 'symbol' not in df.columns: return pd.DataFrame()
    
    df = df[df['symbol'].isin(TICKERS_DATE.keys())].copy()
    if df.empty: return pd.DataFrame()
    
    df = df.set_index('symbol')
    df['bond_price'] = df['c'].astype(float)
    df['payoff'] = df.index.map(PAYOFF)
    df['expiration'] = df.index.map(TICKERS_DATE)
    
    today = date.today()
    df['days_to_exp'] = (pd.to_datetime(df['expiration']).dt.date - today).apply(lambda x: x.days)
    df = df[df['days_to_exp'] > 0] # Filtro de activos vivos
    
    # Cálculos de Tasas (Compuestas)
    df['tem'] = ((df['payoff'] / df['bond_price']) ** (30 / df['days_to_exp']) - 1)
    df['tna'] = ((df['payoff'] / df['bond_price']) - 1) / df['days_to_exp'] * 365
    df['tea'] = ((df['payoff'] / df['bond_price']) ** (365 / df['days_to_exp']) - 1)
    
    # Breakeven y Cobertura
    df['MEP_BREAKEVEN'] = mep * (df['payoff'] / df['bond_price'])
    df['buffer_deval'] = (df['MEP_BREAKEVEN'] / mep) - 1
    
    return df.sort_values('days_to_exp')

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | CARRY MATRIX 2026")

if st.button("🔄 REFRESCAR MERCADO", type="primary", key="btn_main"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_market_data()

if mep_now:
    st.metric("Dólar MEP Referencia", f"${mep_now:,.2f}")
    df_calc = calculate_arbitrage_metrics(mep_now, df_raw)
    
    if not df_calc.empty:
        # --- PESTAÑAS ---
        tab1, tab2, tab3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Cobertura (Breakeven)", "📈 Escenarios USD"])
        
        with tab1:
            st.subheader("Rendimiento Fijo en Pesos")
            st.dataframe(
                df_calc[['bond_price', 'days_to_exp', 'tna', 'tem', 'tea']],
                column_config={
                    "bond_price": st.column_config.NumberColumn("Precio ($)", format="%.2f"),
                    "days_to_exp": st.column_config.NumberColumn("Días Vto."),
                    "tna": st.column_config.NumberColumn("TNA", format="%.2f%%"),
                    "tem": st.column_config.NumberColumn("TEM", format="%.2f%%"),
                    "tea": st.column_config.NumberColumn("TEA", format="%.2f%%"),
                },
                use_container_width=True, height=550
            )
            
        with tab2:
            st.subheader("Punto de Equilibrio Cambiario")
            fig = go.Figure()
            fig.add_hline(y=mep_now, line_dash="dash", line_color="red", annotation_text="MEP Hoy")
            fig.add_trace(go.Scatter(x=df_calc.index, y=df_calc['MEP_BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_calc['MEP_BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3)))
            fig.update_layout(template="plotly_dark", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                df_calc[['bond_price', 'MEP_BREAKEVEN', 'buffer_deval']],
                column_config={
                    "MEP_BREAKEVEN": st.column_config.NumberColumn("MEP Salida (Equilibrio)", format="$%.2f"),
                    "buffer_deval": st.column_config.NumberColumn("Buffer vs Deval", format="%.2f%%")
                },
                use_container_width=True
            )
            
        with tab3:
            st.subheader("Retorno Directo en USD")
            scenarios = [0, 5, 10, 15, 20]
            sim = pd.DataFrame(index=df_calc.index)
            for pct in scenarios:
                mep_fut = mep_now * (1 + pct/100)
                usd_ret = (df_calc['payoff'] / mep_fut) / (df_calc['bond_price'] / mep_now) - 1
                sim[f"MEP +{pct}% (${mep_fut:.0f})"] = usd_ret
            
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True, height=550)
    else:
        st.warning("Los bonos configurados ya vencieron o no están cotizando hoy.")
else:
    st.error("Error de conexión con el feed de datos.")

# BOTÓN FINAL CON KEY ÚNICA
if st.button("🔄 ACTUALIZAR MATRIZ", key="btn_footer"):
    st.cache_data.clear()
    st.rerun()
