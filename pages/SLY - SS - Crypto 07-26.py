import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | CRIPTO ENGINE 4H")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #F3BA2F; font-weight: 800; border-bottom: 3px solid #F3BA2F; }
    .stProgress > div > div > div > div { background-color: #F3BA2F; }
    section[data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E0E0E0; }
    .sector-box { background-color: #FFF8E1; padding: 15px; border-radius: 8px; border-left: 5px solid #FFC107; margin-bottom: 10px; }
    .sector-title { font-weight: bold; color: #7F6000; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY (Sincronizado a 4H)
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        # Normalización de cabeceras CCXT
        df.columns = [c.capitalize() for c in df.columns]
        if 'Vol' in df.columns: df = df.rename(columns={'Vol': 'Volume'})
        
        def dema(s, length):
            ema1 = s.ewm(span=length, adjust=False).mean()
            ema2 = ema1.ewm(span=length, adjust=False).mean()
            return 2 * ema1 - ema2

        # MACD Zero-Lag DEMA
        df['macd_line'] = dema(df['Close'], 12) - dema(df['Close'], 26)
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd_line'] - df['signal_line']
        
        # RSI PRO
        df['rsi_smooth'] = dema(ta.rsi(df['Close'], length=14).fillna(50), 5)

        # Heikin Ashi Recursivo Manual
        ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_o[i] = (ha_o[i-1] + ha_c.iloc[i-1]) / 2
        df['ha_color'] = np.where(ha_c > ha_o, "Verde", "Rojo")
        
        # EMAs de Régimen (52 y 260 velas de 4H)
        df['ema52'] = ta.ema(df['Close'], length=52)
        df['ema260'] = ta.ema(df['Close'], length=260)
        
        return df.fillna(0)
    except Exception as e:
        return pd.DataFrame()

def find_last_signal(df, bear_longs, rsi_filter_active):
    if df.empty or len(df) < 261: return None, None, False, "-"
    
    last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
    
    # Escaneo histórico para detectar persistencia de señal
    for i in range(1, len(df)):
        ema_slow = df['ema260'].iloc[i]
        authorized = (df['ema52'].iloc[i] > ema_slow) if ema_slow != 0 else True
        if bear_longs: authorized = True
        
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_rising = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1]
        
        rsi_zone = True
        if rsi_filter_active:
            rsi_zone = df['rsi_smooth'].iloc[i] < 50

        if not is_active:
            if authorized and ha_flip and macd_accel and rsi_rising and rsi_zone:
                is_active, last_entry_date, last_entry_px = True, df.index[i], df['Close'].iloc[i]
        else:
            # Salida: HA Red + MACD bajando + RSI bajando
            exit_trigger = (df['ha_color'].iloc[i] == "Rojo" and 
                            df['hist'].iloc[i] < df['hist'].iloc[i-1] and 
                            df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1])
            if exit_trigger:
                is_active = False

    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
        
    return last_entry_date, last_entry_px, is_active, verdict

# ─────────────────────────────────────────────
# CONTROL DE EXCHANGE Y DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 60000})

st.title("🛡️ SLY | CRIPTO MONITOR 4H (SWING)")

with st.sidebar:
    st.header("⚙️ Radar 4H Ops")
    min_vol = st.number_input("Volumen Mín 24h (USDT):", value=2000000)
    
    if st.button("📡 1. SINCRONIZAR MERCADO"):
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        st.session_state["all_symbols"] = sorted([s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_vol])
        st.rerun()

    if st.session_state["all_symbols"]:
        batch_size = st.number_input("Activos por Lote:", 10, 100, 40)
        total_lotes = (len(st.session_state["all_symbols"]) // batch_size) + 1
        batch_idx = st.selectbox(f"Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        
        st.subheader("Configuración Swing")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        rsi_filter = st.checkbox("Exigir RSI < 50 (Discount)", value=False)
        
        if st.button("🚀 2. ANALIZAR LOTE 4H", type="primary"):
            ex = get_exchange()
            subset = st.session_state["all_symbols"][batch_idx*batch_size : (batch_idx+1)*batch_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditoría 4H: {sym}")
                    # Descargamos 1000 velas de 4h (~166 días de historial)
                    ohlcv = ex.fetch_ohlcv(sym, timeframe="4h", limit=1000)
                    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['dt'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('dt', inplace=True)
                    
                    data = get_sly_indicators(df)
                    sig_date, sig_px, vigente, verd = find_last_signal(data, bear_longs, rsi_filter)
                    
                    current_close = data['Close'].iloc[-1]
                    pnl_str = f"{((current_close - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.split(":")[0].replace("/USDT", ""),
                        "Última Señal (4H)": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                        "PnL Real": pnl_str,
                        "Veredicto": verd,
                        "Precio": round(current_close, 6),
                        "RSI (4H)": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.1) # Respetar API Rate Limit
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}; st.session_state["all_symbols"] = []; st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE RESULTADOS
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_res = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_res = df_res.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
    st.info(f"Monitorizando {len(df_res)} activos en ciclo de 4 Horas.")
else:
    st.info("👈 Sincronice el mercado y ejecute el escaneo de lotes en 4H.")
