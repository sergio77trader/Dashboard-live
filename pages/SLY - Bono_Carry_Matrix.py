import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3
import numpy as np
import time

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | CARRY TRADE ARG")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.9rem; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS DE BONOS (LECAPS & BONCAPS)
# ─────────────────────────────────────────────
# Datos actualizados de vencimientos y valores finales (Payoff)
TICKERS_DATE = {
    "S31M5": date(2025, 3, 31), "S16A5": date(2025, 4, 16), "S28A5": date(2025, 4, 28),
    "S16Y5": date(2025, 5, 16), "S30Y5": date(2025, 5, 30), "S18J5": date(2025, 6, 18),
    "S30J5": date(2025, 6, 30), "S31L5": date(2025, 7, 31), "S15G5": date(2025, 8, 15),
    "S29G5": date(2025, 8, 29), "S12S5": date(2025, 9, 12), "S30S5": date(2025, 9, 30),
    "T17O5": date(2025, 10, 15), "S31O5": date(2025, 10, 31), "S10N5": date(2025, 11, 10),
    "S28N5": date(2025, 11, 28), "T15D5": date(2025, 12, 15), "T30E6": date(2026, 1, 30),
    "T13F6": date(2026, 2, 13), "TTM26": date(2026, 3, 16), "TTJ26": date(2026, 6, 30),
    "T30J6": date(2026, 6, 30), "TTS26": date(2026, 9, 15), "TTD26": date(2026, 12, 15)
}

PAYOFF = {
    "S31M5": 127.35, "S16A5": 131.21, "S28A5": 130.81, "S16Y5": 136.86,
    "S30Y5": 136.33, "S18J5": 147.69, "S30J5": 146.60, "S31L5": 147.74,
    "S15G5": 146.79, "S29G5": 157.70, "S12S5": 158.97, "S30S5": 159.73,
    "T17O5": 158.87, "S31O5": 132.82, "S10N5": 122.25, "S28N5": 123.56,
    "T15D5": 170.83, "T30E6": 142.22, "T13F6": 144.96, "TTM26": 135.23,
    "TTJ26": 144.62, "T30J6": 144.89, "TTS26": 152.09, "TTD26": 161.14
}

# ─────────────────────────────────────────────
# MOTOR DE EXTRACCIÓN DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_arg_market():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=h).json()
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=h).json()
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=h).json()
        
        mep = pd.DataFrame(r_mep)['close'].median()
        df_assets = pd.DataFrame(r_notes + r_bonds)
        return mep, df_assets
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None

def process_carry_matrix(mep, df):
    if df.empty: return pd.DataFrame()
    
    # Filtrar solo tickers que tenemos en base de datos
    df = df[df['symbol'].isin(TICKERS_DATE.keys())].copy()
    if df.empty: return pd.DataFrame()
    
    df['Precio'] = df['c'].astype(float)
    df['Vencimiento'] = df['symbol'].map(TICKERS_DATE)
    df['Payoff'] = df['symbol'].map(PAYOFF)
    
    # Cálculos Financieros
    today = date.today()
    df['Dias_Vto'] = (pd.to_datetime(df['Vencimiento']).dt.date - today).apply(lambda x: x.days)
    df = df[df['Dias_Vto'] > 0] # Eliminar vencidos
    
    # Tasa Efectiva Mensual (TEM)
    df['TEM'] = ((df['Payoff'] / df['Precio']) ** (30 / df['Dias_Vto']) - 1) * 100
    # Tasa Efectiva Anual (TEA)
    df['TEA'] = ((df['Payoff'] / df['Precio']) ** (365 / df['Dias_Vto']) - 1) * 100
    # MEP de Equilibrio (Breakeven)
    df['MEP_Breakeven'] = mep * (df['Payoff'] / df['Precio'])
    # Buffer vs Devaluación
    df['Buffer_%'] = (df['MEP_Breakeven'] / mep - 1) * 100
    
    return df.sort_values('Dias_Vto')

# ─────────────────────────────────────────────
# INTERFAZ DE USUARIO
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | ARG CARRY MATRIX")
st.markdown("### Monitor de Arbitraje: Pesos (Lecaps) vs Dólar MEP")

mep_ref, df_raw = fetch_arg_market()

if mep_ref:
    st.sidebar.metric("Dólar MEP Hoy", f"${mep_ref:,.2f}")
    
    df_calc = process_carry_matrix(mep_ref, df_raw)
    
    if not df_calc.empty:
        # --- TABLA PRINCIPAL ---
        st.subheader("📊 Análisis de Rendimiento y Cobertura")
        
        # Filtro de Columnas solicitado
        display_cols = ['symbol', 'Precio', 'Dias_Vto', 'TEM', 'TEA', 'MEP_Breakeven', 'Buffer_%']
        
        def style_carry(val):
            if isinstance(val, (int, float)):
                if val > 3.5: return 'color: #00E676; font-weight: bold' # TEM alta
                if val > 1200: return 'color: #00E676; font-weight: bold' # MEP alto
            return ''

        st.dataframe(
            df_calc[display_cols].style.applymap(style_carry, subset=['TEM', 'MEP_Breakeven']),
            column_config={
                "symbol": "Ticker",
                "TEM": st.column_config.NumberColumn("TEM %", format="%.2f%%"),
                "TEA": st.column_config.NumberColumn("TEA %", format="%.2f%%"),
                "MEP_Breakeven": st.column_config.NumberColumn("MEP Equilibrio", format="$%.2f"),
                "Buffer_%": st.column_config.NumberColumn("Buffer Deval", format="%.2f%%")
            },
            use_container_width=True,
            height=500
        )
        
        # --- GRÁFICO DE CURVA DE TASAS ---
        st.divider()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_calc['Dias_Vto'], y=df_calc['TEM'],
            mode='lines+markers', name='Curva TEM',
            line=dict(color='#00E676', width=3),
            hovertemplate='Días: %{x}<br>TEM: %{y:.2f}%'
        ))
        fig.update_layout(
            title="Pendiente de la Curva de Tasas (TEM)",
            xaxis_title="Días al Vencimiento",
            yaxis_title="TEM %",
            template="plotly_dark",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No se encontraron coincidencias para los tickers configurados.")
else:
    st.error("Error al obtener datos de MEP o Bonos.")

if st.button("🔄 ACTUALIZAR MATRIZ"):
    st.cache_data.clear()
    st.rerun()
