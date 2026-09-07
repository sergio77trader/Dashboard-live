import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL MÓDULO DE BONOS
# ─────────────────────────────────────────────
st.title("📡 SLY | BOND PULSE ENGINE")
st.subheader("Auditoría de Deuda Soberana e Indicadores Adelantados")

# ─────────────────────────────────────────────
# MOTOR DE CÁLCULO TÉCNICO (SLY CORE)
# ─────────────────────────────────────────────
def get_bond_signals(ticker):
    try:
        # Descargamos data diaria para ver la inercia
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty: return None
        
        # MACD Zero-Lag (DEMA)
        def dema(s, length):
            ema1 = s.ewm(span=length, adjust=False).mean()
            ema2 = ema1.ewm(span=length, adjust=False).mean()
            return 2 * ema1 - ema2

        fast_ma = dema(df['Close'], 12)
        slow_ma = dema(df['Close'], 26)
        macd_line = fast_ma - slow_ma
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df['hist'] = macd_line - signal_line
        
        # Heikin Ashi para suavizar ruido
        ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['ha_color'] = np.where(ha_close > ha_close.shift(1), "Verde", "Rojo")
        
        return {
            "last_price": float(df['Close'].iloc[-1]),
            "hist_slope": float(df['hist'].iloc[-1] - df['hist'].iloc[-2]),
            "ha_color": df['ha_color'].iloc[-1],
            "prev_hist": float(df['hist'].iloc[-1])
        }
    except: return None

# ─────────────────────────────────────────────
# ANÁLISIS DE RIESGO SOBERANO
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("""<div style='background-color:#F1F8E9; padding:20px; border-radius:10px; border-left:5px solid #2E7D32;'>
        <h4 style='margin:0; color:#1B5E20;'>🇦🇷 BONO AL30D (Soberano Hard Dollar)</h4>
        <p style='font-size:0.9em; color:#546E7A;'>El termómetro principal de la solvencia argentina.</p>
    </div>""", unsafe_allow_html=True)
    
    res_al30 = get_bond_signals("AL30D.BA")
    if res_al30:
        st.metric("Precio AL30D", f"USD {res_al30['last_price']:.2f}", 
                  delta=f"{res_al30['hist_slope']:.4f} Momentum")
        
        if res_al30['prev_hist'] > 0 and res_al30['hist_slope'] > 0:
            st.success("VERDICTO: COMPRESIÓN DE TASAS EN MARCHA (BULLISH)")
        elif res_al30['prev_hist'] < 0 and res_al30['hist_slope'] > 0:
            st.warning("VERDICTO: ACUMULACIÓN EN EL PISO (GIRO DE RIÑÓN)")
        else:
            st.error("VERDICTO: FUGA DE CAPITALES / RIESGO EN ASCENSO")

with col2:
    st.markdown("""<div style='background-color:#E3F2FD; padding:20px; border-radius:10px; border-left:5px solid #1976D2;'>
        <h4 style='margin:0; color:#0D47A1;'>📉 CORRELACIÓN DE RIESGO</h4>
        <p style='font-size:0.9em; color:#546E7A;'>Impacto directo sobre el Equity (Acciones).</p>
    </div>""", unsafe_allow_html=True)
    
    if res_al30:
        if res_al30['ha_color'] == "Verde":
            st.info("💡 **DATO INSTITUCIONAL:** Los bonos están subiendo. Esto bajará el Riesgo País y le dará 'viento de cola' a tus CEDEARs y acciones. El mercado está comprando gobernabilidad.")
        else:
            st.error("⚠️ **ALERTA DE RIESGO:** Los bonos caen. Es probable que las acciones sufran una toma de ganancias o un aumento de la volatilidad en las próximas 48hs.")

# ─────────────────────────────────────────────
# AUDITORÍA DE ESTRATEGIA (CONFLUENCIA)
# ─────────────────────────────────────────────
st.divider()
st.header("🎯 Confluencia de Carteras")

if res_al30 and res_al30['prev_hist'] > 0:
    st.write("✅ **BOND SHIELD ACTIVO:** El flujo soberano respalda tu cartera de acciones. Podes mantener posiciones de riesgo con tranquilidad.")
else:
    st.write("❌ **BOND SHIELD DESACTIVADO:** La caída de bonos indica que el mercado duda de la solvencia. Reducir exposición o ajustar Stop Loss en acciones.")
