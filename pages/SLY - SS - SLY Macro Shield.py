import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACRO SHIELD V2.0")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .macro-card { 
        background-color: #F8F9FA; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 6px solid #004D40; 
        margin-bottom: 20px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
    }
    .macro-title { color: #004D40; font-weight: 800; font-size: 1.2em; margin-bottom: 5px; border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;}
    .verdict-box { padding: 12px; border-radius: 6px; font-weight: bold; margin-top: 12px; text-align: center; font-size: 1.1em; }
    .bullish { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; }
    .bearish { background-color: #FFEBEE; color: #C62828; border: 1px solid #EF9A9A; }
    .neutral { background-color: #ECEFF1; color: #455A64; border: 1px solid #B0BEC5; }
    .explanation { font-size: 0.88em; color: #546E7A; margin-top: 10px; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE DATOS (REDUNDANCIA INSTITUCIONAL)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_macro_data():
    # Tickers: DXY, SPY, RSP, XLY, XLP, HYG, TLT, 10Y (^TNX), 2Y (^IRX - Proxy), TIP (Real Rates)
    tickers = ["DX-Y.NYB", "SPY", "RSP", "XLY", "XLP", "HYG", "TLT", "^TNX", "^IRX", "TIP"]
    data = yf.download(tickers, period="2y", interval="1d", progress=False)['Close']
    return data.ffill()

def analyze_shield():
    df = get_macro_data()
    
    # 1. DXY (Oxígeno)
    dxy_change = (df["DX-Y.NYB"].iloc[-1] / df["DX-Y.NYB"].iloc[-5] - 1) * 100
    
    # 2. Breadth (SPY/RSP)
    breadth = df["SPY"] / df["RSP"]
    breadth_trend = breadth.iloc[-1] > breadth.iloc[-5]
    
    # 3. Smart Money (XLY/XLP)
    rotation = df["XLY"] / df["XLP"]
    rotation_trend = rotation.iloc[-1] > rotation.iloc[-5]

    # 4. Yield Curve Spread (10Y - 2Y)
    # Nota: ^TNX es 10Y en %, ^IRX es 13-week bill como proxy de tasa corta
    spread = df["^TNX"] - df["^IRX"]
    spread_now = spread.iloc[-1]
    spread_prev = spread.iloc[-5]
    
    # 5. Real Rates (TIP)
    # Si el TIP sube, las tasas reales bajan (alcista para Oro/BTC)
    tip_trend = df["TIP"].iloc[-1] > df["TIP"].iloc[-5]

    # 6. Bond Volatility (Proxy MOVE)
    # Analizamos la desviación estándar del TLT
    bond_vol = df["TLT"].pct_change().std() * (252**0.5) * 100
    bond_panic = bond_vol > 15 # Umbral institucional de estrés en bonos

    return {
        "DXY": dxy_change,
        "Breadth": breadth_trend,
        "Rotation": rotation_trend,
        "Spread": (spread_now, spread_prev),
        "TIP": tip_trend,
        "Panic": bond_panic
    }

# ─────────────────────────────────────────────
# LÓGICA DE RENDERIZADO
# ─────────────────────────────────────────────
st.title("🦅 SLY | MACRO SHIELD V2.0")
st.markdown("### Auditoría Forense de Liquidez y Estructura Global")

res = analyze_shield()
c1, c2, c3 = st.columns(3)

with c1:
    # --- DXY ---
    status = "bearish" if res["DXY"] > 0 else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">1. ÍNDICE DÓLAR (DXY)</div>
        Variación Semanal: <b>{res['DXY']:+.2f}%</b>
        <div class="verdict-box {status}">
            {'ALERTA: DÓLAR ASPIRANDO LIQUIDEZ' if status == "bearish" else 'VÍA LIBRE: OXÍGENO EN EL SISTEMA'}
        </div>
        <div class="explanation">
            <b>Veredicto:</b> El DXY mide la escasez de dólares. Si sube, el capital se congela. Si baja, el dinero "quema" en las manos y fluye hacia tus acciones y Cripto.
        </div>
    </div>""", unsafe_allow_html=True)

    # --- SPREAD 10Y-2Y ---
    s_now, s_prev = res["Spread"]
    is_inverted = s_now < 0
    status = "bearish" if is_inverted else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">2. CURVA DE TASAS (10Y-2Y)</div>
        Spread Actual: <b>{s_now:.3f}</b>
        <div class="verdict-box {status}">
            {'CURVA INVERTIDA (RIESGO RECIVO)' if is_inverted else 'CURVA NORMALIZADA (EXPANSIÓN)'}
        </div>
        <div class="explanation">
            <b>Veredicto:</b> Históricamente, una curva invertida precede crisis. El peligro real ocurre cuando la curva se "des-invierte" rápido. Monitorea que este proceso sea lento y ordenado.
        </div>
    </div>""", unsafe_allow_html=True)

with c2:
    # --- BREADTH ---
    status = "bearish" if res["Breadth"] else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">3. AMPLITUD (SPY/RSP)</div>
        Concentración: <b>{'ALTA' if res['Breadth'] else 'SALUDABLE'}</b>
        <div class="verdict-box {status}">
            {'MERCADO FRÁGIL (POCAS LÍDERES)' if status == "bearish" else 'SUBIDA SANA (TODOS PARTICIPAN)'}
        </div>
        <div class="explanation">
            <b>Veredicto:</b> Si el ratio sube, significa que NVIDIA y Apple tapan las caídas del resto. Es un rally artificial. Buscamos que el ratio baje para confirmar un mercado alcista real.
        </div>
    </div>""", unsafe_allow_html=True)

    # --- TASAS REALES (TIP) ---
    status = "bullish" if res["TIP"] else "bearish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">4. TASAS REALES (TIP)</div>
        Dinámica TIP: <b>{'EN ASCENSO' if res['TIP'] else 'EN CAÍDA'}</b>
        <div class="verdict-box {status}">
            {'COMBUSTIBLE PARA ORO/BTC' if status == "bullish" else 'PRESIÓN SOBRE ACTIVOS DUROS'}
        </div>
        <div class="explanation">
            <b>Veredicto:</b> Las Tasas Reales son el enemigo del Oro y Cripto. Si el TIP sube, las tasas reales bajan y el dinero huye del papel moneda hacia activos de escasez.
        </div>
    </div>""", unsafe_allow_html=True)

with c3:
    # --- ROTACIÓN ---
    status = "bullish" if res["Rotation"] else "bearish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">5. ROTACIÓN (XLY/XLP)</div>
        Apetito Sectorial: <b>{'RISK-ON' if res['Rotation'] else 'DEFENSIVO'}</b>
        <div class="verdict-box {status}">
            {'EL CAPITAL BUSCA CRECIMIENTO' if status == "bullish" else 'EL CAPITAL BUSCA REFUGIO'}
        </div>
        <div class="explanation">
            <b>Veredicto:</b> Compara Lujos vs Necesidades. Si XLY domina, hay confianza en el consumo futuro. Si XLP domina, las instituciones se preparan para un invierno económico.
        </div>
    </div>""", unsafe_allow_html=True)

    # --- VOLATILIDAD BONOS (MOVE PROXY) ---
    status = "bearish" if res["Panic"] else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">6. PÁNICO EN BONOS (VOLATILIDAD)</div>
        Estado de Nervios: <b>{'ALTO' if res['Panic'] else 'ESTABLE'}</b>
        <div class="verdict-box {status}">
            {'PÁNICO DETECTADO EN TASAS' if status == "bearish" else 'MERCADO DE TASAS CALMO'}
        </div>
        <div class="explanation">
            <b>Veredicto:</b> Si las tasas bajan pero la volatilidad es alta, el mercado tiene miedo. Si las tasas bajan y hay calma, es el escenario ideal para el "Bull Run" de tu cartera.
        </div>
    </div>""", unsafe_allow_html=True)

st.divider()
st.info("💡 **CONSEJO SLY:** Si el 10Y ha hecho techo, buscamos que el DXY baje (Dimensión 1) y el TIP suba (Dimensión 4). Esa confluencia es la señal de 'All-In' institucional.")
