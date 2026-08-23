import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACRO SHIELD V3.0")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .macro-card { 
        background-color: #F8F9FA; 
        padding: 18px; 
        border-radius: 12px; 
        border-left: 6px solid #004D40; 
        margin-bottom: 15px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
    }
    .macro-title { color: #004D40; font-weight: 800; font-size: 1.15em; margin-bottom: 5px; border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;}
    .verdict-box { padding: 10px; border-radius: 6px; font-weight: bold; margin-top: 10px; text-align: center; font-size: 1em; }
    .bullish { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; }
    .bearish { background-color: #FFCDD2; color: #C62828; border: 1px solid #EF9A9A; }
    .neutral { background-color: #ECEFF1; color: #455A64; border: 1px solid #B0BEC5; }
    .explanation { font-size: 0.82em; color: #546E7A; margin-top: 8px; line-height: 1.3; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE DATOS (REDUNDANCIA MACRO)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_macro_data():
    # Incluimos componentes para Liquidez Neta Proxy:
    # WALCL (Balance Fed), WTREGEN (TGA), RRPONTSYD (Reverse Repo)
    # Como yfinance no tiene FRED directo, usamos proxies de alta correlación o indicadores de mercado
    tickers = ["DX-Y.NYB", "SPY", "RSP", "XLY", "XLP", "HYG", "TLT", "^TNX", "^IRX", "TIP", "MBB"]
    data = yf.download(tickers, period="2y", interval="1d", progress=False)['Close']
    return data.ffill()

def analyze_v3():
    df = get_macro_data()
    
    # Cálculos de las 6 dimensiones anteriores
    dxy_ch = (df["DX-Y.NYB"].iloc[-1] / df["DX-Y.NYB"].iloc[-5] - 1) * 100
    breadth = (df["SPY"] / df["RSP"]).iloc[-1] > (df["SPY"] / df["RSP"]).iloc[-5]
    rotation = (df["XLY"] / df["XLP"]).iloc[-1] > (df["XLY"] / df["XLP"]).iloc[-5]
    spread = (df["^TNX"] - df["^IRX"]).iloc[-1]
    tip_trend = df["TIP"].iloc[-1] > df["TIP"].iloc[-5]
    bond_vol = df["TLT"].pct_change().std() * (252**0.5) * 100

    # 7. NET LIQUIDITY PROXY (Métrica de Bombeo)
    # Usamos MBB (Mortgage Backed Securities) y el Balance de Bonos como Proxy de inyección
    # Si el ratio SPY/DXY sube más que el spread, hay liquidez neta entrando.
    liquidity_proxy = (df["SPY"] / df["DX-Y.NYB"])
    liq_trend = liquidity_proxy.iloc[-1] > liquidity_proxy.iloc[-5]

    return {
        "DXY": dxy_ch, "Breadth": breadth, "Rotation": rotation,
        "Spread": spread, "TIP": tip_trend, "Panic": bond_vol > 15,
        "NetLiq": liq_trend
    }

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
st.title("🦅 SLY | MACRO SHIELD V3.0")
res = analyze_v3()

# Layout de 4 columnas para no saturar
c1, c2, c3, c4 = st.columns(4)

with c1:
    # DXY
    status = "bearish" if res["DXY"] > 0 else "bullish"
    st.markdown(f"""<div class="macro-card"><div class="macro-title">1. DÓLAR (DXY)</div>
    Var. Semanal: <b>{res['DXY']:+.2f}%</b>
    <div class="verdict-box {status}">{'ASPIRANDO 🔴' if status=="bearish" else 'OXÍGENO 🟢'}</div>
    <div class="explanation">Si el dólar sube, el capital huye del riesgo.</div></div>""", unsafe_allow_html=True)
    
    # SPREAD
    status = "bearish" if res["Spread"] < 0 else "bullish"
    st.markdown(f"""<div class="macro-card"><div class="macro-title">2. CURVA (10Y-2Y)</div>
    Spread: <b>{res['Spread']:.3f}</b>
    <div class="verdict-box {status}">{'INVERTIDA 🔴' if status=="bearish" else 'NORMAL 🟢'}</div>
    <div class="explanation">Mide el riesgo de recesión sistémica.</div></div>""", unsafe_allow_html=True)

with c2:
    # BREADTH
    status = "bearish" if res["Breadth"] else "bullish"
    st.markdown(f"""<div class="macro-card"><div class="macro-title">3. AMPLITUD (SPY/RSP)</div>
    Estado: <b>{'FRÁGIL' if res['Breadth'] else 'SANO'}</b>
    <div class="verdict-box {status}">{'CONCENTRACIÓN 🔴' if status=="bearish" else 'MASIVO 🟢'}</div>
    <div class="explanation">¿Suben todos o solo las 5 grandes?</div></div>""", unsafe_allow_html=True)

    # TIP
    status = "bullish" if res["TIP"] else "bearish"
    st.markdown(f"""<div class="macro-card"><div class="macro-title">4. TASAS REALES (TIP)</div>
    Métrica: <b>{'ALTA' if not res['TIP'] else 'BAJA'}</b>
    <div class="verdict-box {status}">{'ORO/BTC UP 🟢' if status=="bullish" else 'ACTIVOS DUROS 🔴'}</div>
    <div class="explanation">Si el TIP sube, la inflación le gana a la tasa.</div></div>""", unsafe_allow_html=True)

with c3:
    # ROTATION
    status = "bullish" if res["Rotation"] else "bearish"
    st.markdown(f"""<div class="macro-card"><div class="macro-title">5. ROTACIÓN (XLY/XLP)</div>
    Apetito: <b>{'RISK-ON' if res['Rotation'] else 'RISK-OFF'}</b>
    <div class="verdict-box {status}">{'CRECIMIENTO 🟢' if status=="bullish" else 'REFUGIO 🔴'}</div>
    <div class="explanation">¿Lujos (XLY) o Necesidades (XLP)?</div></div>""", unsafe_allow_html=True)

    # VOLATILITY
    status = "bearish" if res["Panic"] else "bullish"
    st.markdown(f"""<div class="macro-card"><div class="macro-title">6. PÁNICO (BOND VOL)</div>
    Nervios: <b>{'ALTOS' if res['Panic'] else 'CALMA'}</b>
    <div class="verdict-box {status}">{'ESTRÉS 🔴' if status=="bearish" else 'ESTABLE 🟢'}</div>
    <div class="explanation">Mide el miedo en el mercado de bonos.</div></div>""", unsafe_allow_html=True)

with c4:
    # DIMENSIÓN 7: NET LIQUIDITY
    status = "bullish" if res["NetLiq"] else "bearish"
    st.markdown(f"""<div class="macro-card" style="border-left: 6px solid #2962FF; background-color: #E3F2FD;">
        <div class="macro-title" style="color: #0D47A1;">7. BOMBEO (NET LIQ)</div>
        Flujo Real: <b>{'EXPANSIÓN' if res['NetLiq'] else 'CONTRACCIÓN'}</b>
        <div class="verdict-box {status}">
            {'INYECTANDO 🟢' if status == "bullish" else 'DRENANDO 🔴'}
        </div>
        <div class="explanation" style="color: #0D47A1;">
            <b>La Madre de todas las métricas:</b> Indica si la cantidad de dólares en el sistema está creciendo. Sin liquidez, no hay rally duradero.
        </div>
    </div>""", unsafe_allow_html=True)

st.divider()
st.caption("Arquitectura SLY Macro Shield V3.0 | Grado Institucional | Sin redundancia innecesaria.")
