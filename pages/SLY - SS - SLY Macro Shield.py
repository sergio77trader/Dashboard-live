import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MACRO COMMAND")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .macro-card { 
        background-color: #F8F9FA; padding: 18px; border-radius: 12px; 
        border-left: 6px solid #004D40; margin-bottom: 15px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
    }
    .macro-title { color: #004D40; font-weight: 800; font-size: 1.15em; margin-bottom: 5px; border-bottom: 1px solid #E0E0E0; padding-bottom: 5px;}
    .verdict-box { padding: 10px; border-radius: 6px; font-weight: bold; margin-top: 10px; text-align: center; font-size: 1em; }
    .bullish { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; }
    .bearish { background-color: #FFCDD2; color: #C62828; border: 1px solid #EF9A9A; }
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
    
    # 1. DXY
    dxy_ch = (df["DX-Y.NYB"].iloc[-1] / df["DX-Y.NYB"].iloc[-5] - 1) * 100
    # 2. Spread
    spread = (df["^TNX"] - df["^IRX"]).iloc[-1]
    # 3. Breadth
    br_ratio = df["SPY"] / df["RSP"]
    breadth = br_ratio.iloc[-1] > br_ratio.iloc[-5]
    # 4. TIP (Tasas Reales)
    tip_trend = df["TIP"].iloc[-1] > df["TIP"].iloc[-5]
    # 5. Rotation
    rot_ratio = df["XLY"] / df["XLP"]
    rotation = rot_ratio.iloc[-1] > rot_ratio.iloc[-5]
    # 6. Panic (Bond Vol)
    bond_vol = df["TLT"].pct_change().std() * (252**0.5) * 100
    # 7. Net Liq Proxy
    liq_proxy = (df["SPY"] / df["DX-Y.NYB"])
    liq_trend = liq_proxy.iloc[-1] > liq_proxy.iloc[-5]

    return {
        "DXY": dxy_ch, "Spread": spread, "Breadth": breadth,
        "TIP": tip_trend, "Rotation": rotation, "Panic": bond_vol > 15,
        "NetLiq": liq_trend
    }

# ─────────────────────────────────────────────
# LÓGICA DE RENDERIZADO Y CONCLUSIÓN AI
# ─────────────────────────────────────────────
st.title("🦅 SLY | MÓDULO DE INTELIGENCIA ESTRATÉGICA")
res = analyze_situation()

c1, c2, c3, c4 = st.columns(4)
# (Aquí van los mismos bloques de tarjetas de la V3.0)
with c1:
    s = "bearish" if res["DXY"] > 0 else "bullish"
    st.markdown(f'<div class="macro-card"><div class="macro-title">1. DÓLAR (DXY)</div><b>{res["DXY"]:+.2f}%</b><div class="verdict-box {s}">{"ASPIRANDO 🔴" if s=="bearish" else "OXÍGENO 🟢"}</div></div>', unsafe_allow_html=True)
    s = "bearish" if res["Spread"] < 0 else "bullish"
    st.markdown(f'<div class="macro-card"><div class="macro-title">2. CURVA (10Y-2Y)</div><b>{res["Spread"]:.3f}</b><div class="verdict-box {s}">{"INVERTIDA 🔴" if s=="bearish" else "NORMAL 🟢"}</div></div>', unsafe_allow_html=True)
with c2:
    s = "bearish" if res["Breadth"] else "bullish"
    st.markdown(f'<div class="macro-card"><div class="macro-title">3. AMPLITUD</div><b>{"FRÁGIL" if res["Breadth"] else "SANA"}</b><div class="verdict-box {s}">{"CONCENTRACIÓN 🔴" if s=="bearish" else "MASIVO 🟢"}</div></div>', unsafe_allow_html=True)
    s = "bullish" if res["TIP"] else "bearish"
    st.markdown(f'<div class="macro-card"><div class="macro-title">4. TASAS REALES</div><b>{"EN ASCENSO" if res["TIP"] else "EN CAÍDA"}</b><div class="verdict-box {s}">{"ORO/BTC UP 🟢" if s=="bullish" else "PRESIÓN 🔴"}</div></div>', unsafe_allow_html=True)
with c3:
    s = "bullish" if res["Rotation"] else "bearish"
    st.markdown(f'<div class="macro-card"><div class="macro-title">5. ROTACIÓN</div><b>{"RISK-ON" if res["Rotation"] else "RISK-OFF"}</b><div class="verdict-box {s}">{"CRECIMIENTO 🟢" if s=="bullish" else "REFUGIO 🔴"}</div></div>', unsafe_allow_html=True)
    s = "bearish" if res["Panic"] else "bullish"
    st.markdown(f'<div class="macro-card"><div class="macro-title">6. PÁNICO BONOS</div><b>{"ALTO" if res["Panic"] else "CALMA"}</b><div class="verdict-box {s}">{"ESTRÉS 🔴" if s=="bearish" else "ESTABLE 🟢"}</div></div>', unsafe_allow_html=True)
with c4:
    s = "bullish" if res["NetLiq"] else "bearish"
    st.markdown(f'<div class="macro-card" style="border-left: 6px solid #2962FF; background-color: #E3F2FD;"><div class="macro-title" style="color: #0D47A1;">7. BOMBEO (LIQ)</div><b>{"EXPANSIÓN" if res["NetLiq"] else "CONTRACCIÓN"}</b><div class="verdict-box {s}">{"INYECTANDO 🟢" if s=="bullish" else "DRENANDO 🔴"}</div></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SECCIÓN: SALA DE SITUACIÓN (EL ANÁLISIS)
# ─────────────────────────────────────────────
# Lógica de pesos para el veredicto final
bullish_points = [not res["DXY"] > 0, res["Spread"] > 0, not res["Breadth"], res["TIP"], res["Rotation"], not res["Panic"], res["NetLiq"]].count(True)

st.markdown('<div class="report-box">', unsafe_allow_html=True)
st.markdown('<div class="report-title">🎙️ Informe Forense: Sala de Situación SLY</div>', unsafe_allow_html=True)

# 1. ANÁLISIS DE LIQUIDEZ (Capítulo 1)
liq_status = "FAVORABLE" if (not res["DXY"] > 0 and res["NetLiq"]) else "CRÍTICA"
st.write(f"**CAPA DE LIQUIDEZ:** El entorno de flujo es **{liq_status}**. " + 
         ( "Las tuberías del sistema están inyectando capital, permitiendo que los activos de riesgo ignoren malas noticias." if liq_status == "FAVORABLE" else "El sistema está aspirando dólares; cualquier subida de precio carece de combustible real y es altamente vulnerable." ))

# 2. ANÁLISIS DE ESTRUCTURA (Capítulo 2)
est_status = "SANA" if (res["Spread"] > 0 and not res["Breadth"]) else "FRÁGIL"
st.write(f"**CAPA DE ESTRUCTURA:** La anatomía del mercado se presenta **{est_status}**. " +
         ("La subida es democrática y apoyada por la mayoría de las empresas." if est_status == "SANA" else "Existe una divergencia peligrosa: el índice sube por 5 empresas mientras el resto cae. Es un rally de espejismo."))

# 3. CONCLUSIÓN FINAL
if bullish_points >= 5:
    final_verd = "RIESGO PERMITIDO (FULL RISK-ON) 🟢"
    advise = "El sistema valida la toma de posiciones agresivas. La inercia macro protege tus errores técnicos. Es momento de buscar 'Alpha' en líderes de sector."
elif bullish_points >= 3:
    final_verd = "CAUTELA ESTRATÉGICA (NEUTRAL) 🟡"
    advise = "Existen fuerzas contrapuestas. El mercado puede lateralizar o ser errático. Reducir el tamaño de las posiciones (Equity 40-50%) y esperar confluencia."
else:
    final_verd = "MODO SUPERVIVENCIA (CASH IS KING) 🔴"
    advise = "Liquidación de activos de riesgo sugerida. La física del capital está en contra. Prohibido buscar compras; el sistema prioriza la preservación del equity."

st.markdown(f"""
<div style="margin-top:20px; padding:15px; border: 2px dashed #263238; border-radius:10px;">
    <h3 style="margin:0; color:#263238;">VEREDICTO FINAL: {final_verd}</h3>
    <p style="margin-top:10px; font-size:1.1em;">{advise}</p>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
