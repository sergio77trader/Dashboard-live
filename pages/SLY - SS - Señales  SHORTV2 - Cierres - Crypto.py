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
st.set_page_config(layout="wide", page_title="SLY | MASTER DUAL MONITOR")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
    .sector-box { background-color: #F1F8E9; padding: 15px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-bottom: 10px; }
    .short-box { background-color: #FFEBEE; border-left: 5px solid #C62828; }
    .sector-title { font-weight: bold; color: #1B5E20; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_dual" not in st.session_state:
    st.session_state["master_results_dual"] = {}
if "crypto_list" not in st.session_state:
    st.session_state["crypto_list"] = []

# Mapeo de temporalidades
TF_OPTIONS = {
    "30 MIN": "30m",
    "1 HS": "1h",
    "4 HS": "4h",
    "1 DIA": "1d",
    "1 SEMANA": "1w",
    "1 MES": "1M"
}

# ─────────────────────────────────────────────
# MAPEO SECTORIAL
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "NEAR", "FTM", "ALGO", "ATOM", "SUI", "APT"],
    "DEFI/L2": ["ARB", "OP", "LINK", "UNI", "AAVE", "LDO", "MKR", "SNX", "DYDX", "PENDLE"],
    "AI/DATA": ["RNDR", "FET", "FIL", "THETA", "GRT", "WLD", "ARKM"],
    "MEMES": ["DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF"]
}

def get_crypto_sector(ticker):
    base = ticker.split("/")[0].upper()
    for sector, members in CRYPTO_SECTORS.items():
        if base in members: return sector
    return "ALTCOINS / OTROS"

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY (DEMA ZERO-LAG)
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

# ─────────────────────────────────────────────
# MÁQUINA DE ESTADOS DUAL (LONG & SHORT)
# ─────────────────────────────────────────────
def find_last_signal_dual(df, bear_longs):
    if df.empty or len(df) < 5: return None, None, "CERRADA ⚪", "-"
    last_date, last_px, state, verdict = None, None, "CERRADA ⚪", "-"

    for i in range(1, len(df)):
        bull_reg = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        bear_reg = (df['ema52'].iloc[i] < df['ema260'].iloc[i])
        
        ha_flip_g = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        ha_flip_r = df['ha_color'].iloc[i] == "Rojo" and df['ha_color'].iloc[i-1] == "Verde"
        m_accel_up, m_accel_dw = df['hist'].iloc[i] > df['hist'].iloc[i-1], df['hist'].iloc[i] < df['hist'].iloc[i-1]
        rsi_up, rsi_dw = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1], df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]

        if state == "CERRADA ⚪":
            # LONG: Bull Regime + HA Flip G + MACD Up + RSI Up + RSI < 50
            if bull_reg and ha_flip_g and m_accel_up and rsi_up and df['rsi_smooth'].iloc[i] < 50:
                state, last_date, last_px = "LONG 🟢", df.index[i], df['Close'].iloc[i]
            # SHORT: Bear Regime + HA Flip R + MACD Dw + RSI Dw + RSI > 50
            elif bear_reg and ha_flip_r and m_accel_dw and rsi_dw and df['rsi_smooth'].iloc[i] > 50:
                state, last_date, last_px = "SHORT 🔴", df.index[i], df['Close'].iloc[i]
        
        elif state == "LONG 🟢":
            if df['ha_color'].iloc[i] == "Rojo" and m_accel_dw and rsi_dw: state = "CERRADA ⚪"
        elif state == "SHORT 🔴":
            if df['ha_color'].iloc[i] == "Verde" and m_accel_up and rsi_up: state = "CERRADA ⚪"

    if state != "CERRADA ⚪":
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if "LONG" in state:
            if p_h > 0 and c_h <= 0: verdict = "CERRAR POSICIÓN 🔴"
            elif c_h > p_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"
        else:
            if p_h < 0 and c_h >= 0: verdict = "CERRAR POSICIÓN 🟢"
            elif c_h < p_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"
    return last_date, last_px, state, verdict

# ─────────────────────────────────────────────
# FILTRO DE EXCHANGES
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchanges():
    return ccxt.kucoinfutures(), ccxt.binance({'options': {'defaultType': 'future'}})

def fetch_synced_symbols():
    try:
        ku, bi = get_exchanges()
        k_m, b_m = ku.fetch_markets(), bi.fetch_markets()
        b_bases = {m['base'].upper() for m in b_m if m['active'] and m['quote'] == 'USDT'}
        synced = [m['symbol'] for m in k_m if m['active'] and m['quote'] == 'USDT' and m['base'].upper() in b_bases]
        return sorted(list(set([s for s in synced if not any(x in s for x in ['UP/', 'DOWN/', '3L', '3S'])])))
    except: return []

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | MASTER DUAL MONITOR")

with st.sidebar:
    st.header("⚙️ Configuración")
    selected_tf_label = st.selectbox("Temporalidad de Análisis:", list(TF_OPTIONS.keys()), index=2)
    selected_tf_code = TF_OPTIONS[selected_tf_label]
    
    if st.button("📡 1. Sincronizar Exchanges"):
        st.session_state["crypto_list"] = fetch_synced_symbols()
        st.rerun()

    if st.session_state["crypto_list"]:
        l_size = st.number_input("Acciones por Lote:", 10, 200, 100)
        total_l = (len(st.session_state["crypto_list"]) // l_size) + 1
        batch_idx = st.selectbox(f"Lote (Total: {len(st.session_state['crypto_list'])}):", range(total_l), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs (EMA < 260)", value=True)
        
        if st.button("🚀 2. ACTUALIZAR Y ACUMULAR", type="primary"):
            ku, _ = get_exchanges()
            subset = st.session_state["crypto_list"][batch_idx*l_size : (batch_idx+1)*l_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando {selected_tf_label}: {sym}")
                    raw = ku.fetch_ohlcv(sym, timeframe=selected_tf_code, limit=1000)
                    df = pd.DataFrame(raw, columns=['time','open','high','low','close','vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    sig_date, sig_px, estado, verd = find_last_signal_dual(data, bear_longs)
                    
                    pnl = "-"
                    if "LONG 🟢" in estado: pnl = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%"
                    elif "SHORT 🔴" in estado: pnl = f"{((sig_px - data['Close'].iloc[-1]) / sig_px * 100):.2f}%"
                    
                    last_rsi = data['rsi_smooth'].iloc[-1]
                    st.session_state["master_results_dual"][sym] = {
                        "Activo": sym.split(":")[0].replace("/USDT", ""),
                        "TF": selected_tf_label, "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": estado, "PnL Real": pnl, "Zona RSI": "SOBRE 50 🟢" if last_rsi > 50 else "BAJO 50 🔴",
                        "Veredicto": verd, "Precio": f"{data['Close'].iloc[-1]:.4f}", 
                        "RSI": round(last_rsi, 1), "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.05)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_dual"] = {}; st.session_state["crypto_list"] = []; st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL Y RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["master_results_dual"]:
    df_full = pd.DataFrame(st.session_state["master_results_dual"].values())
    df_vigentes = df_full[df_full["Estado"] != "CERRADA ⚪"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN (VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby(["Sector", "Estado"])["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                color = "sector-box" if "LONG" in row['Estado'] else "sector-box short-box"
                st.markdown(f"<div class='{color}'><div class='sector-title'>{row['Sector']} | {row['Estado']}</div><div>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    
    st.subheader(f"📋 Matriz Dual ({selected_tf_label})")
    def color_cells(val):
        str_v = str(val)
        if "LONG" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v or "SOBRE 50" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str_v or "BAJISTA" in str_v or "BAJO 50" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''
    st.dataframe(df_full.style.map(color_cells), use_container_width=True, height=600)
else: st.info("Sincronice e inicie el radar.")
