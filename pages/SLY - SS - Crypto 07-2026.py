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
st.set_page_config(layout="wide", page_title="SLY | CRIPTO DUAL MONITOR")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #F3BA2F; }
    .sector-box { background-color: #FFF3E0; padding: 15px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .short-box { background-color: #FFEBEE; border-left: 5px solid #C62828; }
    .sector-title { font-weight: bold; color: #BF360C; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}

# ─────────────────────────────────────────────
# MAPEO SECTORIAL
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC/USDT", "ETH/USDT"],
    "LAYER 1": ["SOL/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "NEAR/USDT", "FTM/USDT", "ALGO/USDT"],
    "DEFI/L2": ["ARB/USDT", "OP/USDT", "LINK/USDT", "UNI/USDT", "AAVE/USDT", "LDO/USDT"],
    "AI/DEPIN": ["RNDR/USDT", "FET/USDT", "FIL/USDT", "THETA/USDT"],
    "MEMES": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT", "FLOKI/USDT"]
}

def get_crypto_sector(ticker):
    for sector, members in CRYPTO_SECTORS.items():
        if ticker.upper() in members: return sector
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
    if df.empty or len(df) < 2: return None, None, "CERRADA ⚪", "-"
    last_date, last_px, state, verdict = None, None, "CERRADA ⚪", "-"

    for i in range(1, len(df)):
        bull_regime = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        bear_regime = (df['ema52'].iloc[i] < df['ema260'].iloc[i])
        
        # Gatillos Long
        ha_flip_g = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        m_accel_up = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_up = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1]
        
        # Gatillos Short
        ha_flip_r = df['ha_color'].iloc[i] == "Rojo" and df['ha_color'].iloc[i-1] == "Verde"
        m_accel_dw = df['hist'].iloc[i] < df['hist'].iloc[i-1]
        rsi_dw = df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]

        if state == "CERRADA ⚪":
            # ENTRADA LONG
            if bull_regime and ha_flip_g and m_accel_up and rsi_up and df['rsi_smooth'].iloc[i] < 50:
                state, last_date, last_px = "LONG 🟢", df.index[i], df['Close'].iloc[i]
            # ENTRADA SHORT
            elif bear_regime and ha_flip_r and m_accel_dw and rsi_dw and df['rsi_smooth'].iloc[i] > 50:
                state, last_date, last_px = "SHORT 🔴", df.index[i], df['Close'].iloc[i]

        elif state == "LONG 🟢":
            if df['ha_color'].iloc[i] == "Rojo" and m_accel_dw and rsi_dw: state = "CERRADA ⚪"
        elif state == "SHORT 🔴":
            if df['ha_color'].iloc[i] == "Verde" and m_accel_up and rsi_up: state = "CERRADA ⚪"

    if state != "CERRADA ⚪":
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if state == "LONG 🟢":
            if p_h > 0 and c_h <= 0: verdict = "CERRAR POSICIÓN 🔴"
            elif c_h > p_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"
        else: # SHORT
            if p_h < 0 and c_h >= 0: verdict = "CERRAR POSICIÓN 🟢"
            elif c_h < p_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"
            
    return last_date, last_px, state, verdict

# ─────────────────────────────────────────────
# INTERFAZ Y CONECTIVIDAD DUAL
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchanges():
    return ccxt.kucoin(), ccxt.binance()

def fetch_synced_symbols():
    try:
        ku, bi = get_exchanges()
        k_m = ku.load_markets()
        b_m = bi.load_markets()
        # Solo USDT y activos en ambos
        k_syms = {s for s in k_m if '/USDT' in s and k_m[s]['active']}
        b_syms = {s for s in b_m if '/USDT' in s and b_m[s]['active']}
        common = k_syms.intersection(b_syms)
        # Limpieza de tokens apalancados
        filtered = [s for s in common if not any(x in s for x in ['UP/', 'DOWN/', 'BEAR/', 'BULL/', '3L', '3S'])]
        return sorted(list(filtered))
    except: return []

st.title("🛡️ SLY | CRIPTO DUAL SIGNAL 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    if st.button("📡 Sincronizar Binance + KuCoin"):
        st.session_state["crypto_list"] = fetch_synced_symbols()
        st.rerun()

    if "crypto_list" in st.session_state:
        lote_size = st.number_input("Tamaño Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ku, _ = get_exchanges() # Usamos KuCoin para la data OHLCV
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando 4H: {sym}")
                    raw = ku.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw, columns=['time','open','high','low','close','vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    sig_date, sig_px, estado, verd = find_last_signal_dual(data, bear_longs)
                    
                    pnl = "-"
                    if "LONG" in estado: pnl = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%"
                    elif "SHORT" in estado: pnl = f"{((sig_px - data['Close'].iloc[-1]) / sig_px * 100):.2f}%"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", ""), "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": estado, "PnL Real": pnl, "Veredicto": verd,
                        "Precio": f"{data['Close'].iloc[-1]:.4f}", "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.1)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}; st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL DUAL
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_vigentes = df_full[df_full["Estado"] != "CERRADA ⚪"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN (VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby(["Sector", "Estado"])["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                box_class = "sector-box" if "LONG" in row['Estado'] else "sector-box short-box"
                st.markdown(f"<div class='{box_class}'><div class='sector-title'>{row['Sector']} | {row['Estado']}</div><div>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    
    st.subheader("📋 Matriz Cripto 4H (Dual)")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[True, True])
    def color_cells(val):
        str_v = str(val)
        if "LONG" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''
    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else: st.info("Sincronice e inicie el radar.")
