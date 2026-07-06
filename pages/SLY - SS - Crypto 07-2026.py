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
    .stProgress > div > div > div > div { background-color: #E65100; }
    .sector-box { background-color: #FFF3E0; padding: 15px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #BF360C; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}
if "synced_crypto_list" not in st.session_state:
    st.session_state["synced_crypto_list"] = []

# ─────────────────────────────────────────────
# MAPEO SECTORIAL CRIPTO
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "NEAR", "FTM", "ALGO", "ATOM", "SUI", "APT"],
    "DEFI/L2": ["ARB", "OP", "LINK", "UNI", "AAVE", "LDO", "MKR", "SNX"],
    "AI/DATA": ["RNDR", "FET", "FIL", "THETA", "GRT", "WLD", "ARKM"],
    "MEMES": ["DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF"]
}

def get_crypto_sector(ticker):
    # Extraemos el base (BTC de BTC/USDT:USDT)
    base = ticker.split("/")[0].upper()
    for sector, members in CRYPTO_SECTORS.items():
        if base in members: return sector
    return "ALTCOINS / PERPS"

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY (4H)
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        df.columns = [c.capitalize() for c in df.columns]
        df = df.dropna(subset=['Close'])

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
    if df.empty or len(df) < 2: return None, None, False, "-"
    last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
    
    for i in range(1, len(df)):
        authorized = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
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
# FILTRO BINANCE + KUCOIN SYNC (PERPETUALS)
# ─────────────────────────────────────────────
@st.cache_resource
def get_kucoin(): return ccxt.kucoinfutures({'enableRateLimit': True})

@st.cache_resource
def get_binance(): return ccxt.binance({'options': {'defaultType': 'future'}})

def fetch_synced_symbols():
    try:
        ku = get_kucoin()
        bi = get_binance()
        
        # Obtener mercados de ambos
        k_markets = ku.load_markets()
        b_markets = bi.load_markets()
        
        # 1. Extraer símbolos base de Binance (BTC, ETH, etc.) que operen en USDT
        b_bases = {b_markets[s]['base'] for s in b_markets if b_markets[s]['active'] and b_markets[s]['quote'] == 'USDT'}
        
        # 2. Filtrar KuCoin: Solo los que existan en Binance
        synced = []
        for s in k_markets:
            m = k_markets[s]
            # Debe ser USDT lineal, activo, y estar en la lista de Binance
            if m['active'] and m['quote'] == 'USDT' and m['linear'] and m['base'] in b_bases:
                # Evitar tokens de predicción o basura
                if 'USDT' in s and ':' in s:
                    synced.append(s)
                    
        return sorted(synced)
    except Exception as e:
        st.error(f"Error de Sincronización: {e}")
        return []

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | CRIPTO DUAL MASTER 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    
    if st.button("📡 Sincronizar Binance + KuCoin"):
        st.session_state["synced_crypto_list"] = fetch_synced_symbols()
        st.rerun()

    if st.session_state["synced_crypto_list"]:
        total_found = len(st.session_state["synced_crypto_list"])
        st.success(f"Activos en común: {total_found}")
        
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 50)
        total_lotes = (total_found // lote_size) + 1
        batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_kucoin()
            subset = st.session_state["synced_crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando 4H: {sym}")
                    # 1000 velas para estabilidad de EMA 260
                    raw_data = ex.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    
                    sig_date, sig_px, vigente, verd = find_last_signal(data, bear_longs)
                    pnl_val = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.split(":")[0].replace("/USDT", ""), 
                        "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                        "PnL Real": pnl_val, "Veredicto": verd,
                        "Precio": f"{data['Close'].iloc[-1]:.4f}", "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.1)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}
        st.session_state["synced_crypto_list"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL Y RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN (VIGENTES EN BINANCE)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="sector-box">
                    <div class="sector-title">{row['Sector']}: {len(row['Activo'])} Activos</div>
                    <div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div>
                </div>
                """, unsafe_allow_html=True)
    
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
    st.info("👈 Sincronice exchanges y analice lotes para visualizar la matriz.")
