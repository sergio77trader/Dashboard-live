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
    h1 { color: #F3BA2F; font-weight: 800; border-bottom: 3px solid #F3BA2F; }
    .stProgress > div > div > div > div { background-color: #F3BA2F; }
    .sector-box { background-color: #F1F8E9; padding: 15px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-bottom: 10px; }
    .sector-title { font-weight: bold; color: #1B5E20; font-size: 1.1em; }
    .short-box { background-color: #FFEBEE; border-left: 5px solid #C62828; }
    .short-title { color: #B71C1C; }
</style>
""", unsafe_allow_html=True)

if "crypto_master_results" not in st.session_state:
    st.session_state["crypto_master_results"] = {}
if "crypto_symbols" not in st.session_state:
    st.session_state["crypto_symbols"] = []

# ─────────────────────────────────────────────
# MAPEO SECTORIAL
# ─────────────────────────────────────────────
CRYPTO_SECTOR_MAP = {
    "BITCOIN": ["BTC/USDT", "BTC"],
    "ETHEREUM": ["ETH/USDT", "ETH"],
    "TOP ALTS": ["SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "LTC/USDT", "BCH/USDT", "LINK/USDT"],
    "AI & L2": ["RNDR/USDT", "FET/USDT", "NEAR/USDT", "ARB/USDT", "OP/USDT", "STX/USDT", "GRT/USDT"],
    "MEME COINS": ["PEPE/USDT", "SHIB/USDT", "BONK/USDT", "WIF/USDT", "FLOKI/USDT"]
}

def get_crypto_sector(ticker):
    clean_sym = ticker.split(":")[0].replace("/USDT", "").upper()
    for sector, members in CRYPTO_SECTOR_MAP.items():
        if clean_sym in [m.upper().replace("/USDT", "") for m in members]: return sector
    return "OTROS / DEGEN"

# ─────────────────────────────────────────────
# MOTOR TÉCNICO ZERO-LAG DEMA
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
# MÁQUINA DE ESTADOS DUAL (LONG & SHORT)
# ─────────────────────────────────────────────
def find_last_signal_dual(df):
    if df.empty or len(df) < 2: return None, None, "CERRADA ⚪", "-"
    
    last_date, last_px = None, None
    state = "CERRADA ⚪" # Estados: "LONG 🟢", "SHORT 🔴", "CERRADA ⚪"
    verdict = "-"

    for i in range(1, len(df)):
        # Variables de Inercia
        bull_regime = df['ema52'].iloc[i] > df['ema260'].iloc[i]
        bear_regime = df['ema52'].iloc[i] < df['ema260'].iloc[i]
        
        # Gatillos de Precio y Motor
        ha_green = df['ha_color'].iloc[i] == "Verde"
        ha_red = df['ha_color'].iloc[i] == "Rojo"
        ha_flip_g = ha_green and df['ha_color'].iloc[i-1] == "Rojo"
        ha_flip_r = ha_red and df['ha_color'].iloc[i-1] == "Verde"
        
        m_accel_up = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        m_accel_dw = df['hist'].iloc[i] < df['hist'].iloc[i-1]
        
        rsi_up = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1]
        rsi_dw = df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]

        # --- LÓGICA DE ENTRADA ---
        if state == "CERRADA ⚪":
            # Entrar LONG: Bull Regime + HA Flip G + MACD Accel Up + RSI Up + RSI < 50
            if bull_regime and ha_flip_g and m_accel_up and rsi_up and df['rsi_smooth'].iloc[i] < 50:
                state, last_date, last_px = "LONG 🟢", df.index[i], df['Close'].iloc[i]
            # Entrar SHORT: Bear Regime + HA Flip R + MACD Accel Dw + RSI Dw + RSI > 50
            elif bear_regime and ha_flip_r and m_accel_dw and rsi_dw and df['rsi_smooth'].iloc[i] > 50:
                state, last_date, last_px = "SHORT 🔴", df.index[i], df['Close'].iloc[i]

        # --- LÓGICA DE SALIDA ---
        elif state == "LONG 🟢":
            if ha_red and m_accel_dw and rsi_dw: state = "CERRADA ⚪"
        elif state == "SHORT 🔴":
            if ha_green and m_accel_up and rsi_up: state = "CERRADA ⚪"

    # Veredicto dinámico para posiciones abiertas
    if state != "CERRADA ⚪":
        curr_h, prev_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if state == "LONG 🟢":
            if prev_h > 0 and curr_h <= 0: verdict = "CERRAR POSICIÓN ❌"
            elif curr_h > prev_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"
        elif state == "SHORT 🔴":
            if prev_h < 0 and curr_h >= 0: verdict = "CERRAR POSICIÓN ❌"
            elif curr_h < prev_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"

    return last_date, last_px, state, verdict

# ─────────────────────────────────────────────
# MOTOR DE DATOS CCXT
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | CRIPTO DUAL MONITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    min_vol = st.number_input("Volumen Mín 24h (USDT):", value=5000000)
    if st.button("📡 1. SINCRONIZAR MERCADO"):
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        st.session_state["crypto_symbols"] = sorted([s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_vol])
        st.rerun()

    if st.session_state["crypto_symbols"]:
        batch_size = st.number_input("Acciones por Lote:", 10, 100, 30)
        total_lotes = (len(st.session_state["crypto_symbols"]) // batch_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        
        if st.button("🚀 2. ACTUALIZAR Y ACUMULAR"):
            ex = get_exchange()
            subset = st.session_state["crypto_symbols"][batch_idx*batch_size : (batch_idx+1)*batch_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                    ohlcv = ex.fetch_ohlcv(sym, timeframe="4h", limit=1000)
                    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['dt'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('dt', inplace=True)
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    
                    sig_date, sig_px, estado, verd = find_last_signal_dual(data)
                    
                    # Cálculo de PnL Real (Diferente para Long y Short)
                    pnl = "-"
                    if "🟢" in estado:
                        pnl = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%"
                    elif "🔴" in estado:
                        pnl = f"{((sig_px - data['Close'].iloc[-1]) / sig_px * 100):.2f}%"
                    
                    st.session_state["crypto_master_results"][sym] = {
                        "Activo": sym.split(":")[0], "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": estado, "PnL Real": pnl, "Veredicto": verd,
                        "Precio": round(data['Close'].iloc[-1], 4),
                        "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                except: continue
                time.sleep(0.1)
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["crypto_master_results"] = {}; st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL DUAL
# ─────────────────────────────────────────────
if st.session_state["crypto_master_results"]:
    df_full = pd.DataFrame(st.session_state["crypto_master_results"].values())
    df_vigentes = df_full[df_full["Estado"] != "CERRADA ⚪"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN (POSICIONES VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby(["Sector", "Estado"])["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                box_class = "sector-box" if "🟢" in row['Estado'] else "sector-box short-box"
                title_class = "sector-title" if "🟢" in row['Estado'] else "sector-title short-title"
                st.markdown(f"""
                <div class="{box_class}">
                    <div class="{title_class}">{row['Sector']} | {row['Estado']} ({len(row['Activo'])})</div>
                    <div style='font-size: 0.85em;'>{", ".join(row['Activo'])}</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.subheader("📋 Matriz Cripto 4H (Long & Short)")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[True, True])
    
    def color_cells(val):
        str_v = str(val)
        if "LONG 🟢" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT 🔴" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "CERRADA ⚪" in str_v or "POSICIÓN ❌" in str_v: return 'background-color: #F5F5F5; color: #9E9E9E;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else: st.info("Sincronice e inicie el escaneo.")
