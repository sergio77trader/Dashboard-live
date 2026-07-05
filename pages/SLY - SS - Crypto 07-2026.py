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
st.set_page_config(layout="wide", page_title="SLY | MASTER CRIPTO DUAL")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #F3BA2F; }
    .sector-box { background-color: #FFF3E0; padding: 15px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; }
    .sector-title { font-weight: bold; color: #BF360C; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}
if "crypto_list" not in st.session_state:
    st.session_state["crypto_list"] = []

# ─────────────────────────────────────────────
# MAPEO SECTORIAL
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "NEAR", "FTM", "ALGO", "ATOM", "LINK", "SUI", "APT", "SEI"],
    "AI & DATA": ["RNDR", "FET", "FIL", "THETA", "NEAR", "AGIX", "OCEAN", "WLD", "ARKM"],
    "DEFI/L2": ["ARB", "OP", "UNI", "AAVE", "LDO", "MKR", "SNX", "DYDX", "PENDLE"],
    "MEMES": ["DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF", "BOME"]
}

def get_crypto_sector(ticker):
    base = ticker.split("/")[0].upper()
    for sector, members in CRYPTO_SECTORS.items():
        if base in members: return sector
    return "ALTCOINS / OTROS"

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        df.columns = [c.capitalize() for c in df.columns]
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

def find_last_signal(df, bear_longs):
    if df.empty or len(df) < 5: return None, None, False, "-"
    last_signal_date, last_signal_px, is_active, verdict = None, None, False, "-"
    
    for i in range(1, len(df)):
        authorized = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        m_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_ok = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1] and df['rsi_smooth'].iloc[i] < 50
        
        if not is_active and (authorized and ha_flip and m_accel and rsi_ok):
            is_active, last_signal_date, last_signal_px = True, df.index[i], df['Close'].iloc[i]
        elif is_active and (df['ha_color'].iloc[i] == "Rojo" and df['hist'].iloc[i] < df['hist'].iloc[i-1] and df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]):
            is_active = False

    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
    return last_signal_date, last_signal_px, is_active, verdict

# ─────────────────────────────────────────────
# FILTRO DE EXCHANGES (Sincronización Corregida)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchanges():
    return ccxt.kucoin(), ccxt.binance()

def fetch_filtered_symbols(min_vol):
    try:
        ku, bi = get_exchanges()
        # Cargamos los mercados de Binance para ver qué hay disponible
        b_m = bi.fetch_markets()
        b_bases = {m['base'].upper() for m in b_m if m['quote'] == 'USDT' and m['active']}
        
        # Cargamos los mercados de KuCoin
        k_m = ku.fetch_markets()
        tickers = ku.fetch_tickers() # Obtenemos volúmenes reales
        
        synced = []
        for m in k_m:
            symbol = m['symbol']
            base = m['base'].upper()
            quote = m['quote'].upper()
            
            # Condición: Activo en KuCoin, Par USDT, y EXISTE en Binance
            if m['active'] and quote == 'USDT' and base in b_bases:
                # Obtener volumen con fallback a 0
                ticker_info = tickers.get(symbol, {})
                vol = ticker_info.get('quoteVolume', 0)
                
                # Filtrar tokens apalancados/basura
                if vol >= min_vol and not any(x in symbol for x in ['UP/', 'DOWN/', '3L', '3S', 'BULL', 'BEAR']):
                    synced.append(symbol)
        
        return sorted(list(set(synced)))
    except Exception as e:
        st.error(f"Error en Sincronización: {e}")
        return []

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | MASTER DUAL MONITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    # Bajamos el volumen por defecto a 1M para ver más activos
    min_vol = st.number_input("Volumen Mín 24h (USDT):", value=1000000)
    
    if st.button("📡 Sincronizar Binance + KuCoin"):
        with st.spinner("Cruzando bases de datos de exchanges..."):
            st.session_state["crypto_list"] = fetch_filtered_symbols(min_vol)
        st.rerun()

    if st.session_state["crypto_list"]:
        total_l = len(st.session_state["crypto_list"])
        st.success(f"Activos Sincronizados: {total_l}")
        
        l_size = st.number_input("Acciones por Lote:", 10, 200, 100)
        num_lotes = (total_l // l_size) + (1 if total_l % l_size > 0 else 0)
        batch_idx = st.selectbox(f"Lote:", range(num_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ku, _ = get_exchanges()
            subset = st.session_state["crypto_list"][batch_idx*l_size : (batch_idx+1)*l_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                    raw = ku.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw, columns=['time','open','high','low','close','vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    sig_date, sig_px, active, verd = find_last_signal(data, bear_longs)
                    
                    pnl = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (active and sig_px) else "-"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", "").replace(":USDT",""), 
                        "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "No encontrada",
                        "Estado": "VIGENTE 🟢" if active else "CERRADA 🔴", 
                        "PnL Real": pnl, "Veredicto": verd,
                        "Precio": f"{data['Close'].iloc[-1]:.4f}", 
                        "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                except: continue
                time.sleep(0.05)
            st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]

    st.subheader("📊 EXPOSICIÓN VIGENTE POR SECTOR")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"<div class='sector-box'><div class='sector-title'>{row['Sector']}: {len(row['Activo'])}</div><div>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    
    st.subheader("📋 Matriz Cripto 4H (Binance Synced)")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''
    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else: st.info("Sincronice e inicie el radar.")
