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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | OMNI-SYNC V52")

st.markdown("""
<style>
    .stDataFrame { font-size: 0.75rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stTabs [aria-selected="true"] { background-color: #00E676 !important; color: black !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE PAYOFFS (TASAS FIJAS)
# ─────────────────────────────────────────────
# Solo estos permiten cálculo de Carry Trade (TEM/Breakeven)
FIXED_CONFIG = {
    "S31M6": {"vto": date(2026, 3, 31), "p": 103.85}, "S16M6": {"vto": date(2026, 3, 16), "p": 102.10},
    "S17A6": {"vto": date(2026, 4, 17), "p": 107.50}, "S30A6": {"vto": date(2026, 4, 30), "p": 108.90},
    "S29Y6": {"vto": date(2026, 5, 29), "p": 111.65}, "S30J6": {"vto": date(2026, 6, 30), "p": 115.40},
    "S31L6": {"vto": date(2026, 7, 31), "p": 119.55}, "S31G6": {"vto": date(2026, 8, 31), "p": 124.10},
    "S30S6": {"vto": date(2026, 9, 30), "p": 128.45}, "S30O6": {"vto": date(2026, 10, 30), "p": 132.85},
    "S30N6": {"vto": date(2026, 11, 30), "p": 137.45}, "S30D6": {"vto": date(2026, 12, 30), "p": 142.25},
    "TTM26": {"vto": date(2026, 3, 16), "p": 135.24}, "TTJ26": {"vto": date(2026, 6, 30), "p": 144.63},
    "T30J6": {"vto": date(2026, 6, 30), "p": 144.90}, "TTS26": {"vto": date(2026, 9, 15), "p": 152.10},
    "TTD26": {"vto": date(2026, 12, 15), "p": 161.14}, "T15E7": {"vto": date(2027, 1, 15), "p": 165.80}
}

# ─────────────────────────────────────────────
# LÓGICA DE CLASIFICACIÓN (TU LISTA)
# ─────────────────────────────────────────────
def classify_bond(ticker):
    t = str(ticker).upper().strip()
    if t.endswith('D') or t.endswith('C'): return 'Especie C/D (Cable/MEP)'
    if t.startswith('S') and any(c.isdigit() for c in t): return 'Lecap (Tasa Fija)'
    if (t.startswith('T') or t.startswith('TT')) and 'X' not in t: return 'Boncap (Tasa Fija)'
    if t.startswith('X') or t.startswith('TX') or t in ['DICP','PARP','CUAP','PAP0','DIP0']: return 'Bono CER (Inflación)'
    if t.startswith('AL') or t.startswith('GD') or t.startswith('AE'): return 'Bono Hard Dollar (Soberano)'
    if any(t.startswith(p) for p in ['BA','BP','CO','BDC','PBY','ARC']): return 'Bono Provincial'
    return 'Otros / Sin Clasificar'

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_all_data():
    h = {'User-Agent': 'Mozilla/5.0'}
    endpoints = {
        "MEP": "https://data912.com/live/mep",
        "L": "https://data912.com/live/arg_letras",
        "N": "https://data912.com/live/arg_notes",
        "B": "https://data912.com/live/arg_bonds"
    }
    mep = 1250.0
    raw = []
    for key, url in endpoints.items():
        try:
            r = requests.get(url, verify=False, timeout=10, headers=h).json()
            if key == "MEP": mep = pd.DataFrame(r)['close'].median()
            else: raw.extend(r)
        except: continue
    return mep, pd.DataFrame(raw)

# ─────────────────────────────────────────────
# PROCESAMIENTO
# ─────────────────────────────────────────────
def build_matrices(mep, df):
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    df['symbol'] = df['symbol'].str.replace(" ", "").str.upper()
    
    carry_list = []
    today = date.today()

    for _, row in df.iterrows():
        sym = row['symbol']
        price = float(row['c'])
        # Solo calculamos Carry para los que tenemos el Payoff cargado
        for tid, info in FIXED_CONFIG.items():
            if tid in sym and not (sym.endswith('D') or sym.endswith('C')):
                days = (info['vto'] - today).days
                if days > 0 and price > 0:
                    carry_list.append({
                        "Ticker": tid, "Precio": price, "Días": days, "Payoff": info['p'],
                        "TEM": ((info['p'] / price) ** (30 / days) - 1),
                        "TEA": ((info['p'] / price) ** (365 / days) - 1),
                        "TNA": ((info['p'] / price) - 1) / days * 365,
                        "BREAKEVEN": mep * (info['p'] / price)
                    })
                break
    
    # Clasificar todo para el Inspector
    df['Categoría'] = df['symbol'].apply(classify_bond)
    return pd.DataFrame(carry_list), df[['Categoría', 'symbol', 'c', 'v', 'p']]

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | OMNI-BOND V52")

mep_val, raw_df = fetch_all_data()

if mep_val:
    st.metric("Dólar MEP Hoy", f"${mep_val:,.2f}")
    df_carry, df_inspect = build_matrices(mep_val, raw_df)
    
    tabs = st.tabs(["📊 Matriz Carry (Pesos)", "🛡️ Breakeven MEP", "📈 Escenarios USD", "🔍 INSPECTOR CLASIFICADO"])
    
    with tabs[0]:
        if not df_carry.empty:
            st.dataframe(df_carry.sort_values("Días").style.format({
                'TEM': '{:.2%}', 'TNA': '{:.2%}', 'TEA': '{:.2%}', 'Precio': '${:.2f}'
            }), use_container_width=True, height=500)
        else: st.warning("No hay letras fijas detectadas para calcular.")

    with tabs[1]:
        if not df_carry.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_carry['Ticker'], y=df_carry['BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_carry['BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3)))
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        if not df_carry.empty:
            sim = pd.DataFrame(index=df_carry['Ticker'])
            for pct in [0, 5, 10, 15, 20]:
                mep_f = mep_val * (1 + pct/100)
                sim[f"Dólar +{pct}%"] = (df_carry.set_index('Ticker')['Payoff'] / mep_f) / (df_carry.set_index('Ticker')['Precio'] / mep_val) - 1
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True)

    with tabs[3]:
        st.subheader("Auditoría de Activos ByMA")
        f_cat = st.multiselect("Filtrar Categoría:", df_inspect['Categoría'].unique(), default=df_inspect['Categoría'].unique())
        st.dataframe(df_inspect[df_inspect['Categoría'].isin(f_cat)].sort_values(['Categoría','symbol']), use_container_width=True, height=600)

if st.button("🔄 ACTUALIZAR", key="refresh"):
    st.cache_data.clear()
    st.rerun()
