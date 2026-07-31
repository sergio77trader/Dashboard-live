import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MASTER CRIPTO 4H")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
    .sector-box { background-color: #FFF3E0; padding: 15px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #BF360C; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}

# ─────────────────────────────────────────────
# MAPEO SECTORIAL
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "NEAR", "FTM", "ALGO", "ATOM", "SUI", "APT"],
    "DEFI/L2": ["ARB", "OP", "LINK", "UNI", "AAVE", "LDO", "MKR", "SNX"],
    "AI/DATA": ["RNDR", "FET", "FIL", "THETA", "GRT"],
    "MEMES": ["DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF"]
}

def get_crypto_sector(ticker):
    base = ticker.split("/")[0].upper()
    for sector, members in CRYPTO_SECTORS.items():
        if base in members: return sector
    return "ALTCOINS / PERPS"

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY (DEMA ZERO-LAG)
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        # Normalización de columnas para compatibilidad universal
        df.columns = [c.capitalize() for c in df.columns]
        
        def dema(s, length):
            ema1 = s.ewm(span=length, adjust=False).mean()
            ema2 = ema1.ewm(span=length, adjust=False).mean()
            return 2 * ema1 - ema2

        # MACD Zero-Lag
        df['macd_line'] = dema(df['Close'], 12) - dema(df['Close'], 26)
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd_line'] - df['signal_line']
        
        # RSI PRO
        df['rsi_smooth'] = dema(ta.rsi(df['Close'], length=14).fillna(50), 5)

        # Heikin Ashi Recursivo Manual
        ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
        for i in range(1, len(df)): ha_o[i] = (ha_o[i-1] + ha_c.iloc[i-1]) / 2
        df['ha_color'] = np.where(ha_c > ha_o, "Verde", "Rojo")
        
        # EMAs de Régimen
        df['ema52'] = ta.ema(df['Close'], length=52)
        df['ema260'] = ta.ema(df['Close'], length=260)
        
        return df
    except: return pd.DataFrame()

def find_last_signal_audit(df, bear_longs):
    if df.empty or len(df) < 30: return None, None, None, None, False, "-"
    
    last_entry_date, last_entry_px = None, None
    last_exit_date, last_exit_px = None, None
    is_active = False
    verdict = "-"
    
    # Rastrear señal en el historial
    for i in range(1, len(df)):
        # Si la EMA 260 no existe aún, autorizamos por defecto si es Bullish o bear_longs
        ema_v = df['ema260'].iloc[i]
        authorized = (df['ema52'].iloc[i] > ema_v if not np.isnan(ema_v) else True) or bear_longs
        
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        m_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_ok = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1] and df['rsi_smooth'].iloc[i] < 50
        
        # Entrada
        if not is_active and (authorized and ha_flip and m_accel and rsi_ok):
            is_active = True
            last_entry_date, last_entry_px = df.index[i], df['Close'].iloc[i]
            last_exit_date, last_exit_px = None, None
        
        # Salida
        elif is_active and (df['ha_color'].iloc[i] == "Rojo" and df['hist'].iloc[i] < df['hist'].iloc[i-1] and df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]):
            is_active = False
            last_exit_date, last_exit_px = df.index[i], df['Close'].iloc[i]

    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
    
    return last_entry_date, last_entry_px, last_exit_date, last_exit_px, is_active, verdict

# ─────────────────────────────────────────────
# CONECTIVIDAD KUCOIN FUTURES
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({'enableRateLimit': True})

def fetch_symbols():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        symbols = [s for s in markets if '/USDT:USDT' in s and markets[s]['active']]
        return sorted(symbols)
    except: return []

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | CRIPTO MASTER AUDITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    if st.button("📡 1. Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()

    if "crypto_list" in st.session_state:
        lote_size = st.number_input("Acciones por Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        
        if st.button("🚀 2. ANALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                    raw = ex.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw, columns=['time','open','high','low','close','vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    
                    data = get_sly_indicators(df)
                    ent_dt, ent_px, exit_dt, exit_px, active, verd = find_last_signal_audit(data, bear_longs)
                    
                    # Cálculo de PnL según estado
                    curr_px = data['Close'].iloc[-1]
                    if active:
                        pnl = ((curr_px - ent_px) / ent_px) * 100
                        status = "VIGENTE 🟢"
                    elif ent_px and exit_px:
                        pnl = ((exit_px - ent_px) / ent_px) * 100
                        status = "CERRADA 🔴"
                    else:
                        pnl, status = 0.0, "SIN SEÑAL ⚪"

                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT:USDT", ""),
                        "Últ. Señal": ent_dt.strftime('%d/%m %H:%M') if ent_dt else "-",
                        "Estado": status,
                        "PnL Real": f"{pnl:.2f}%" if ent_px else "-",
                        "Veredicto": verd if active else ("Cerrada" if exit_px else "-"),
                        "Precio": f"{curr_px:.4f}",
                        "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.05)
                except: continue
            st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_res = pd.DataFrame(st.session_state["master_results_crypto"].values())
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else: st.info("Sincronice e inicie el escaneo.")
