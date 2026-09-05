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
st.set_page_config(layout="wide", page_title="SLY | CRIPTO MONITOR 4H")

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
# MAPEO SECTORIAL CRIPTO (BÓVEDA DE NARRATIVAS)
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADERS": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"],
    "AI & DATA": ["RNDR/USDT", "FET/USDT", "NEAR/USDT", "GRT/USDT", "OCEAN/USDT"],
    "LAYER 1/2": ["ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "ARB/USDT", "OP/USDT", "FTM/USDT"],
    "DEFI": ["UNI/USDT", "LINK/USDT", "AAVE/USDT", "LDO/USDT", "MKR/USDT"],
    "MEME COINS": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT", "WIF/USDT", "FLOKI/USDT"],
    "INFRA": ["FIL/USDT", "THETA/USDT", "STX/USDT", "HNT/USDT"]
}

def get_sector(ticker):
    for sector, members in CRYPTO_SECTORS.items():
        if ticker.upper() in members: return sector
    return "ALTCOINS / OTROS"

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY (4H)
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        # Normalizar para CCXT (vienen en minúsculas)
        df.columns = [c.capitalize() for c in df.columns]
        df = df.rename(columns={'Vol': 'Volume'})
        
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

        # Heikin Ashi Recursivo
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

def find_last_signal(df, bear_longs):
    df_clean = df.dropna(subset=['ema260'])
    if df_clean.empty or len(df_clean) < 2: return None, None, False, "-"
    
    last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
    for i in range(1, len(df_clean)):
        authorized = (df_clean['ema52'].iloc[i] > df_clean['ema260'].iloc[i]) or bear_longs
        ha_flip = df_clean['ha_color'].iloc[i] == "Verde" and df_clean['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df_clean['hist'].iloc[i] > df_clean['hist'].iloc[i-1]
        rsi_ok = df_clean['rsi_smooth'].iloc[i] > df_clean['rsi_smooth'].iloc[i-1] and df_clean['rsi_smooth'].iloc[i] < 50
        
        if not is_active and (authorized and ha_flip and macd_accel and rsi_ok):
            is_active, last_entry_date, last_entry_px = True, df_clean.index[i], df_clean['Close'].iloc[i]
        elif is_active and (df_clean['ha_color'].iloc[i] == "Rojo" and df_clean['hist'].iloc[i] < df_clean['hist'].iloc[i-1] and df_clean['rsi_smooth'].iloc[i] < df_clean['rsi_smooth'].iloc[i-1]):
            is_active = False

    if is_active:
        c_h, p_h = df_clean['hist'].iloc[-1], df_clean['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
    return last_entry_date, last_entry_px, is_active, verdict

def get_macro_status(symbol, ex):
    """Analiza la inercia del MACD en 1D para el veredicto Macro Cripto"""
    try:
        ohlcv = ex.fetch_ohlcv(symbol, timeframe='1d', limit=50)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        hist = macd['MACDh_12_26_9']
        curr, prev = hist.iloc[-1], hist.iloc[-2]
        if curr > prev: return "Ganando Fuerza (1D) 🟢"
        return "Perdiendo Fuerza (1D) 🔴"
    except: return "Neutral ⚪"

# ─────────────────────────────────────────────
# CONECTIVIDAD KUCOIN FUTURES
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({'enableRateLimit': True, 'timeout': 30000})

@st.cache_data(ttl=300)
def fetch_symbols(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        # Solo perpetuos USDT con volumen mínimo
        valid = [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_vol]
        return sorted(valid)
    except: return []

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | CRIPTO MONITOR 4H (PERPETUOS)")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    min_vol = st.number_input("Volumen Mín 24h (USDT):", value=5000000)
    
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols(min_vol)
        st.rerun()

    if "crypto_list" in st.session_state:
        lote_size = st.number_input("Acciones por Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs (4H)", value=True)
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando 4H: {sym}")
                    raw_data = ex.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw_data, columns=['time','open','high','low','close','vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    
                    data_4h = get_sly_indicators(df)
                    sig_date, sig_px, vigente, verd = find_last_signal(data_4h, bear_longs)
                    
                    macro_v = get_macro_status(sym, ex)
                    pnl_str = f"{((df['close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.split(":")[0], "Sector": get_sector(sym),
                        "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                        "PnL Real": pnl_str, "Veredicto": verd, "MACD Macro": macro_v,
                        "Última Señal": sig_date.strftime('%Y-%m-%d %H:%M') if sig_date else "-",
                        "Precio": f"{df['close'].iloc[-1]:.4f}", "RSI": round(data_4h['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data_4h['ema52'].iloc[-1] > data_4h['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.1) # Rate limit protection
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}
        st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL Y MATRIZ
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN CRIPTO (VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"<div class='sector-box'><div class='sector-title'>{row['Sector']}: {len(row['Activo'])}</div><div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    else: st.warning("Sin posiciones abiertas en 4H.")

    st.subheader("📋 Matriz de Señales Cripto 4H")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v or "Ganando Fuerza" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v or "Perdiendo Fuerza" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v or "Neutral" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else: st.info("👈 Sincronice con KuCoin y analice lotes en 4H.")
