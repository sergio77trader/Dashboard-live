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
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #004D40; }
    .stProgress > div > div > div > div { background-color: #004D40; }
    .sector-box { background-color: #F1F8E9; padding: 15px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #1B5E20; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []

# ─────────────────────────────────────────────
# MAPEO SECTORIAL CRIPTO
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "BITCOIN": ["BTC/USDT", "BTC"],
    "ETHEREUM": ["ETH/USDT", "ETH"],
    "TOP ALTS": ["SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "LTC/USDT"],
    "AI & L2": ["RNDR/USDT", "FET/USDT", "NEAR/USDT", "ARB/USDT", "OP/USDT", "LINK/USDT", "STX/USDT"],
    "MEME COINS": ["PEPE/USDT", "SHIB/USDT", "BONK/USDT", "WIF/USDT", "FLOKI/USDT"]
}

def get_crypto_sector(ticker):
    clean_sym = ticker.split(":")[0].upper()
    for sector, members in CRYPTO_SECTORS.items():
        if clean_sym in [m.upper() for m in members]: return sector
    return "OTROS / DEGEN"

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY (ZERO-LAG DEMA)
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'vol': 'Volume'})
        def dema(s, length):
            ema1 = s.ewm(span=length, adjust=False).mean()
            ema2 = ema1.ewm(span=length, adjust=False).mean()
            return 2 * ema1 - ema2

        df['macd_line'] = dema(df['Close'], 12) - dema(df['Close'], 26)
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd_line'] - df['signal_line']
        df['rsi_smooth'] = dema(ta.rsi(df['Close'], length=14).fillna(50), 5)
        
        ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
        for i in range(1, len(df)): ha_o[i] = (ha_o[i-1] + ha_c.iloc[i-1]) / 2
        df['ha_color'] = np.where(ha_c > ha_o, "Verde", "Rojo")
        
        df['ema52'] = ta.ema(df['Close'], length=52)
        df['ema260'] = ta.ema(df['Close'], length=260)
        return df.dropna(subset=['ema260'])
    except: return pd.DataFrame()

# ─────────────────────────────────────────────
# MÁQUINA DE ESTADOS (RASTREO HISTÓRICO 4H)
# ─────────────────────────────────────────────
def find_last_signal(df, bear_longs):
    if df.empty or len(df) < 2: return None, None, False, "-"
    last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
    
    for i in range(1, len(df)):
        authorized = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        # RSI Rising + RSI < 50 (Filtro original del script 1)
        rsi_ok = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1] and df['rsi_smooth'].iloc[i] < 50
        
        if not is_active and (authorized and ha_flip and macd_accel and rsi_ok):
            is_active, last_entry_date, last_entry_px = True, df.index[i], df['Close'].iloc[i]
        elif is_active and (df['ha_color'].iloc[i] == "Rojo" and df['hist'].iloc[i] < df['hist'].iloc[i-1] and df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]):
            is_active = False

    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
    return last_entry_date, last_entry_px, is_active, verdict

# ─────────────────────────────────────────────
# INTERFAZ Y DATOS CCXT
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

st.title("🛡️ SLY | CRIPTO SIGNAL MONITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    min_vol = st.number_input("Volumen Mín 24h (USDT):", value=5000000)
    if st.button("📡 1. SINCRONIZAR MERCADO"):
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        st.session_state["all_symbols"] = sorted([s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_vol])
        st.rerun()

    if st.session_state["all_symbols"]:
        batch_size = st.number_input("Acciones por Lote:", 10, 200, 30)
        total_lotes = (len(st.session_state["all_symbols"]) // batch_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Bear-Longs (4H)", value=True)
        
        if st.button("🚀 2. ACTUALIZAR Y ACUMULAR"):
            ex = get_exchange()
            subset = st.session_state["all_symbols"][batch_idx*batch_size : (batch_idx+1)*batch_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Analizando: {sym}")
                    ohlcv = ex.fetch_ohlcv(sym, timeframe="4h", limit=1000)
                    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['dt'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('dt', inplace=True)
                    
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    
                    sig_date, sig_px, vigente, verd = find_last_signal(data, bear_longs)
                    pnl_str = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.split(":")[0], "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                        "PnL Real": pnl_str, "Veredicto": verd, "Precio": round(data['Close'].iloc[-1], 4),
                        "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                except: continue
                time.sleep(0.1)
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}; st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL Y TABLA MAESTRA
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN (POSICIONES ABIERTAS 4H)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"<div class='sector-box'><div class='sector-title'>{row['Sector']}: {len(row['Activo'])}</div><div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    
    st.subheader("📋 Matriz Cripto 4H (Acumulada)")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else:
    st.info("Sincronice el mercado y actualice lotes en 4H para ver resultados.")
