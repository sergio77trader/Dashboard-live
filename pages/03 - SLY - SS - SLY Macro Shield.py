import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACRO COMMAND V4.0")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .macro-card { 
        background-color: #F8F9FA; padding: 18px; border-radius: 12px; 
        border-left: 6px solid #004D40; margin-bottom: 15px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
        min-height: 320px;
    }
    .macro-title { color: #004D40; font-weight: 800; font-size: 1.15em; margin-bottom: 5px; border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;}
    .verdict-box { padding: 10px; border-radius: 6px; font-weight: bold; margin-top: 10px; text-align: center; font-size: 1em; }
    .bullish { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; }
    .bearish { background-color: #FFCDD2; color: #C62828; border: 1px solid #EF9A9A; }
    .manual-text { font-size: 0.82em; color: #455A64; margin-top: 12px; line-height: 1.4; border-top: 1px dashed #CFD8DC; padding-top: 10px; }
    .manual-label { font-weight: bold; color: #263238; text-transform: uppercase; font-size: 0.85em; }
    .report-box { background-color: #ECEFF1; padding: 25px; border-radius: 15px; border: 2px solid #263238; margin-top: 30px; }
    .report-title { color: #263238; font-weight: 900; font-size: 1.5em; text-transform: uppercase; margin-bottom: 15px; border-bottom: 3px solid #263238; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_macro_data():
    tickers = ["DX-Y.NYB", "SPY", "RSP", "XLY", "XLP", "HYG", "TLT", "^TNX", "^IRX", "TIP"]
    data = yf.download(tickers, period="2y", interval="1d", progress=False)['Close']
    return data.ffill()

def analyze_situation():
    df = get_macro_data()
    dxy_ch = (df["DX-Y.NYB"].iloc[-1] / df["DX-Y.NYB"].iloc[-5] - 1) * 100
    spread = (df["^TNX"] - df["^IRX"]).iloc[-1]
    br_ratio = df["SPY"] / df["RSP"]
    breadth = br_ratio.iloc[-1] > br_ratio.iloc[-5]
    tip_trend = df["TIP"].iloc[-1] > df["TIP"].iloc[-5]
    rot_ratio = df["XLY"] / df["XLP"]
    rotation = rot_ratio.iloc[-1] > rot_ratio.iloc[-5]
    bond_vol = df["TLT"].pct_change().std() * (252**0.5) * 100
    liq_proxy = (df["SPY"] / df["DX-Y.NYB"])
    liq_trend = liq_proxy.iloc[-1] > liq_proxy.iloc[-5]

    return {
        "DXY": dxy_ch, "Spread": spread, "Breadth": breadth,
        "TIP": tip_trend, "Rotation": rotation, "Panic": bond_vol > 15,
        "NetLiq": liq_trend
    }

# ─────────────────────────────────────────────
# UI: RENDERIZADO CON EXPLICACIONES
# ─────────────────────────────────────────────
st.title("🛡️ SLY | MASTER MACRO MONITOR & MANUAL")
res = analyze_situation()

c1, c2, c3, c4 = st.columns(4)

with c1:
    # --- 1. DXY ---
    s = "bearish" if res["DXY"] > 0 else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">1. DÓLAR (DXY)</div>
        Var. Semanal: <b>{res['DXY']:+.2f}%</b>
        <div class="verdict-box {s}">{'ASPIRANDO 🔴' if s=="bearish" else 'OXÍGENO 🟢'}</div>
        <div class="manual-text">
            <span class="manual-label">¿Qué es?</span> El precio del efectivo.<br>
            <span class="manual-label">Lógica:</span> Si el DXY sube, el dólar se vuelve escaso y "succiona" el dinero de las acciones. Si baja, hay vía libre para que el mercado suba.
        </div>
    </div>""", unsafe_allow_html=True)
    
    # --- 2. SPREAD ---
    s = "bearish" if res["Spread"] < 0 else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">2. CURVA (10Y-2Y)</div>
        Spread: <b>{res['Spread']:.3f}</b>
        <div class="verdict-box {s}">{'INVERTIDA 🔴' if s=="bearish" else 'NORMAL 🟢'}</div>
        <div class="manual-text">
            <span class="manual-label">¿Qué es?</span> La diferencia entre tasas largas y cortas.<br>
            <span class="manual-label">Lógica:</span> Si es negativa (Invertida), el mercado predice recesión. Si es positiva, estamos en fase de expansión económica saludable.
        </div>
    </div>""", unsafe_allow_html=True)

with c2:
    # --- 3. BREADTH ---
    s = "bearish" if res["Breadth"] else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">3. AMPLITUD (SPY/RSP)</div>
        Estado: <b>{'FRÁGIL' if res['Breadth'] else 'SANO'}</b>
        <div class="verdict-box {s}">{'CONCENTRACIÓN 🔴' if s=="bearish" else 'MASIVO 🟢'}</div>
        <div class="manual-text">
            <span class="manual-label">¿Qué es?</span> Ponderado vs Equitativo.<br>
            <span class="manual-label">Lógica:</span> Compara si el mercado sube gracias a todas las empresas (Sano) o si Nvidia y Apple están tapando las caídas de las otras 495 (Frágil).
        </div>
    </div>""", unsafe_allow_html=True)

    # --- 4. TASAS REALES ---
    s = "bullish" if res["TIP"] else "bearish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">4. TASAS REALES (TIP)</div>
        Métrica: <b>{'BAJA' if res['TIP'] else 'ALTA'}</b>
        <div class="verdict-box {s}">{'ORO/BTC UP 🟢' if s=="bullish" else 'ACTIVOS DUROS 🔴'}</div>
        <div class="manual-text">
            <span class="manual-label">¿Qué es?</span> Tasa de interés menos inflación.<br>
            <span class="manual-label">Lógica:</span> El combustible de Bitcoin y el Oro. Si el TIP sube, la moneda pierde valor real y el capital huye hacia activos de escasez (BTC/Oro).
        </div>
    </div>""", unsafe_allow_html=True)

with c3:
    # --- 5. ROTACIÓN ---
    s = "bullish" if res["Rotation"] else "bearish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">5. ROTACIÓN (XLY/XLP)</div>
        Apetito: <b>{'RISK-ON' if res['Rotation'] else 'DEFENSIVO'}</b>
        <div class="verdict-box {s}">{'CRECIMIENTO 🟢' if s=="bullish" else 'REFUGIO 🔴'}</div>
        <div class="manual-text">
            <span class="manual-label">¿Qué es?</span> Lujos vs Necesidades básicas.<br>
            <span class="manual-label">Lógica:</span> Si el dinero va a Tesla/Amazon (XLY), hay optimismo. Si va a Coca-Cola/Walmart (XLP), las instituciones tienen miedo y se protegen.
        </div>
    </div>""", unsafe_allow_html=True)

    # --- 6. PÁNICO ---
    s = "bearish" if res["Panic"] else "bullish"
    st.markdown(f"""<div class="macro-card">
        <div class="macro-title">6. PÁNICO (BOND VOL)</div>
        Nervios: <b>{'ALTOS' if res['Panic'] else 'CALMA'}</b>
        <div class="verdict-box {s}">{'ESTRÉS 🔴' if s=="bearish" else 'ESTABLE 🟢'}</div>
        <div class="manual-text">
            <span class="manual-label">¿Qué es?</span> La volatilidad del mercado de bonos.<br>
            <span class="manual-label">Lógica:</span> Si las tasas bajan con calma, las acciones suben. Si las tasas bajan con pánico (alta vol), las acciones caen por "vuelo a la calidad".
        </div>
    </div>""", unsafe_allow_html=True)

with c4:
    # --- 7. NET LIQUIDITY ---
    s = "bullish" if res["NetLiq"] else "bearish"
    st.markdown(f"""<div class="macro-card" style="border-left: 6px solid #2962FF; background-color: #E3F2FD;">
        <div class="macro-title" style="color: #0D47A1;">7. BOMBEO (NET LIQ)</div>
        Flujo: <b>{'EXPANSIÓN' if res['NetLiq'] else 'CONTRACCIÓN'}</b>
        <div class="verdict-box {s}">{'INYECTANDO 🟢' if s=="bullish" else 'DRENANDO 🔴'}</div>
        <div class="manual-text" style="color: #0D47A1;">
            <span class="manual-label">¿Qué es?</span> Cantidad de dólares real.<br>
            <span class="manual-label">Lógica:</span> La madre de todas las métricas. Si las tuberías del sistema están inyectando dólares, el mercado subirá aunque no haya buenas noticias.
        </div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SALA DE SITUACIÓN
# ─────────────────────────────────────────────
bullish_points = [not res["DXY"] > 0, res["Spread"] > 0, not res["Breadth"], res["TIP"], res["Rotation"], not res["Panic"], res["NetLiq"]].count(True)

st.markdown('<div class="report-box">', unsafe_allow_html=True)
st.markdown('<div class="report-title">🎙️ Sala de Situación: Análisis de Riesgo Actual</div>', unsafe_allow_html=True)

if bullish_points >= 5:
    st.success(f"VEREDICTO: RIESGO PERMITIDO ({bullish_points}/7 Puntos) - Las condiciones macro son óptimas.")
elif bullish_points >= 3:
    st.warning(f"VEREDICTO: CAUTELA ESTRATÉGICA ({bullish_points}/7 Puntos) - Fuerzas contrapuestas detectadas.")
else:
    st.error(f"VEREDICTO: MODO SUPERVIVENCIA ({bullish_points}/7 Puntos) - La física del capital ordena salida.")

st.markdown("</div>", unsafe_allow_html=True)
