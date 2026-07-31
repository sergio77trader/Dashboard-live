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
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "NEAR", "FTM", "ALGO", "ATOM", "SUI", "APT"],
    "DEFI/L2": ["ARB", "OP", "LINK", "UNI", "AAVE", "LDO", "MKR", "SNX", "DYDX"],
    "AI/DATA": ["RNDR", "FET", "FIL", "THETA", "GRT", "ARKM", "WLD"],
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
# MÁQUINA DE ESTADOS DUAL (AUDIT TRAIL)
# ─────────────────────────────────────────────
def find_last_signal_dual(df, bear_longs):
    if df.empty or len(df) < 2: return None, None, None, None, "CERRADA ⚪", "-"
    
    last_entry_date, last_entry_px = None, None
    last_exit_date, last_exit_px = None, None
    state = "CERRADA ⚪"
    verdict = "-"

    for i in range(1, len(df)):
        bull_reg = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        bear_reg = (df['ema52'].iloc[i] < df['ema260'].iloc[i])
        
        ha_flip_g = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        ha_flip_r = df['ha_color'].iloc[i] == "Rojo" and df['ha_color'].iloc[i-1] == "Verde"
        m_accel_up = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        m_accel_dw = df['hist'].iloc[i] < df['hist'].iloc[i-1]
        rsi_up = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1]
        rsi_dw = df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]

        if state == "CERRADA ⚪":
            # ENTRADA LONG
            if bull_reg and ha_flip_g and m_accel_up and rsi_up and df['rsi_smooth'].iloc[i] < 50:
                state, last_entry_date, last_entry_px = "LONG 🟢", df.index[i], df['Close'].iloc[i]
                last_exit_date, last_exit_px = None, None
            # ENTRADA SHORT
            elif bear_reg and ha_flip_r and m_accel_dw and rsi_dw and df['rsi_smooth'].iloc[i] > 50:
                state, last_entry_date, last_entry_px = "SHORT 🔴", df.index[i], df['Close'].iloc[i]
                last_exit_date, last_exit_px = None, None

        elif state == "LONG 🟢":
            if df['ha_color'].iloc[i] == "Rojo" and m_accel_dw and rsi_dw:
                state, last_exit_date, last_exit_px = "CERRADA ⚪", df.index[i], df['Close'].iloc[i]
        elif state == "SHORT 🔴":
            if df['ha_color'].iloc[i] == "Verde" and m_accel_up and rsi_up:
                state, last_exit_date, last_exit_px = "CERRADA ⚪", df.index[i], df['Close'].iloc[i]

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
            
    return last_entry_date, last_entry_px, last_exit_date, last_exit_px, state, verdict

# ─────────────────────────────────────────────
# FILTRO DE EXCHANGES
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchanges():
    return ccxt.kucoinfutures(), ccxt.binance()

def fetch_synced_symbols():
    try:
        ku, bi = get_exchanges()
        b_m = bi.fetch_markets()
        b_bases = {m['base'].upper() for m in b_m if m['quote'] == 'USDT' and m['active']}
        k_m = ku.fetch_markets()
        synced = []
        for m in k_m:
            if m['active'] and m['quote'] == 'USDT' and m['base'].upper() in b_bases:
                if not any(x in m['symbol'] for x in ['UP/', 'DOWN/', '3L', '3S']):
                    synced.append(m['symbol'])
        return sorted(list(set(synced)))
    except: return []

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | MASTER DUAL MONITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    if st.button("📡 Sincronizar Binance + KuCoin"):
        st.session_state["crypto_list"] = fetch_synced_symbols()
        st.rerun()

    if "crypto_list" in st.session_state:
        l_size = st.number_input("Acciones por Lote:", 10, 200, 100)
        total_l = (len(st.session_state["crypto_list"]) // l_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_l), format_func=lambda x: f"Lote {x+1}")
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
                    
                    ent_dt, ent_px, ex_dt, ex_px, estado, verd = find_last_signal_dual(data, bear_longs)
                    
                    # Cálculo de PnL y Fechas
                    pnl_final = "-"
                    if "LONG" in estado:
                        pnl_final = f"{((data['Close'].iloc[-1] - ent_px) / ent_px * 100):.2f}%"
                    elif "SHORT" in estado:
                        pnl_final = f"{((ent_px - data['Close'].iloc[-1]) / ent_px * 100):.2f}%"
                    elif estado == "CERRADA ⚪" and ent_px and ex_px:
                        # Si está cerrada, calculamos el resultado final de la última operación
                        # Detectamos si la última fue Long o Short basándonos en la lógica
                        # Para simplificar: PnL del cierre respecto a la entrada
                        diff = (ex_px - ent_px) / ent_px * 100
                        # Nota: Aquí se asume el último sentido.
                        pnl_final = f"{diff:.2f}%"

                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.split(":")[0].replace("/USDT", ""),
                        "Sector": get_crypto_sector(sym),
                        "Última Entrada": ent_dt.strftime('%d/%m %H:%M') if ent_dt else "-",
                        "Último Cierre": ex_dt.strftime('%d/%m %H:%M') if ex_dt else "-",
                        "Estado": estado, 
                        "PnL": pnl_final, 
                        "Veredicto": verd,
                        "Precio": f"{data['Close'].iloc[-1]:.4f}", 
                        "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.05)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}; st.session_state["crypto_list"] = []; st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL Y RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_vigentes = df_full[df_full["Estado"] != "CERRADA ⚪"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN VIGENTE")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby(["Sector", "Estado"])["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                box_class = "sector-box" if "LONG" in row['Estado'] else "sector-box short-box"
                st.markdown(f"<div class='{box_class}'><div class='sector-title'>{row['Sector']} | {row['Estado']}</div><div>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    
    st.subheader("📋 Matriz Cripto 4H (Dual Perpetual)")
    def color_cells(val):
        str_v = str(val)
        if "LONG" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''
    st.dataframe(df_full.style.map(color_cells), use_container_width=True, height=600)
else: st.info("Sincronice e inicie el radar.")
