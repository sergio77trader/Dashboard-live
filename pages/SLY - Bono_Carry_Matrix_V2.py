import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | CARRY MATRIX 2026")

# BASE DE DATOS ACTUALIZADA (CURVA 2026 - 2027)
TICKERS_DATE = {
    # LECAPS 2026 (S)
    "S31M6": date(2026, 3, 31), "S17A6": date(2026, 4, 17), "S29Y6": date(2026, 5, 29),
    "S30J6": date(2026, 6, 30), "S31L6": date(2026, 7, 31), "S31G6": date(2026, 8, 31),
    "S30S6": date(2026, 9, 30), "S30O6": date(2026, 10, 30), "S30N6": date(2026, 11, 30),
    "S30D6": date(2026, 12, 30),
    # BONCAPS 2026/27 (T / TT)
    "TTM26": date(2026, 3, 16), "TTJ26": date(2026, 6, 30), "T30J6": date(2026, 6, 30),
    "TTS26": date(2026, 9, 15), "TTD26": date(2026, 12, 15), "T15E7": date(2027, 1, 15),
    "T15M7": date(2027, 3, 15), "T15J7": date(2027, 6, 15)
}

# Valores de rescate (Payoff) estimados al vencimiento (Capital + Interés)
PAYOFF = {
    "S31M6": 103.50, "S17A6": 107.20, "S29Y6": 111.40, "S30J6": 115.10,
    "S31L6": 119.30, "S31G6": 123.80, "S30S6": 128.20, "S30O6": 132.50,
    "S30N6": 137.10, "S30D6": 142.00, "TTM26": 135.24, "TTJ26": 144.63,
    "T30J6": 144.90, "TTS26": 152.10, "TTD26": 161.14, "T15E7": 165.80,
    "T15M7": 172.30, "T15J7": 181.50
}

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
    except: return None, None

def calculate_metrics(mep, df):
    if df.empty: return pd.DataFrame()
    df = df[df['symbol'].isin(TICKERS_DATE.keys())].copy()
    df = df.set_index('symbol')
    df['price'] = df['c'].astype(float)
    df['payoff'] = df.index.map(PAYOFF)
    df['exp'] = df.index.map(TICKERS_DATE)
    df['days'] = (pd.to_datetime(df['exp']).dt.date - date.today()).apply(lambda x: x.days)
    df = df[df['days'] > 0]
    
    # Tasas
    df['TEM'] = ((df['payoff'] / df['price']) ** (30 / df['days']) - 1) * 100
    df['TEA'] = ((df['payoff'] / df['price']) ** (365 / df['days']) - 1) * 100
    df['BREAKEVEN'] = mep * (df['payoff'] / df['price'])
    return df.sort_values('days')

# INTERFAZ
st.title("💸 CARRY TRADE MATRIX 2026")

mep_now, df_raw = fetch_market_data()

if mep_now and not df_raw.empty:
    st.metric("Dólar MEP", f"${mep_now:,.2f}")
    df_calc = calculate_metrics(mep_now, df_raw)
    
    if not df_calc.empty:
        t1, t2 = st.tabs(["📊 Tasas", "📈 Breakeven"])
        with t1:
            st.dataframe(df_calc[['price', 'days', 'TEM', 'TEA']], use_container_width=True)
        with t2:
            st.dataframe(df_calc[['BREAKEVEN']], use_container_width=True)
    else:
        st.warning("Los bonos en código ya vencieron o no hay data en el mercado.")
else:
    st.error("Error de conexión.")

if st.button("🔄 ACTUALIZAR", key="btn_refresh"):
    st.cache_data.clear()
    st.rerun()
