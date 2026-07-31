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
# MAPEO SECTORIAL CRIPTO
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC/USDT", "ETH/USDT"],
    "LAYER 1": ["SOL/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "NEAR/USDT", "FTM/USDT", "ALGO/USDT"],
    "DEFI/L2": ["ARB/USDT", "OP/USDT", "LINK/USDT", "UNI/USDT", "AAVE/USDT", "LDO/USDT"],
    "AI/DEPIN": ["RNDR/USDT", "FET/USDT", "FIL/USDT", "THETA/USDT"],
    "MEMES": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT", "FLOKI/USDT"],
    "EXCHANGE": ["BNB/USDT", "KCS/USDT", "OKB/USDT"]
}

def get_crypto_sector(ticker):
    for sector, members in CRYPTO_SECTORS.items():
        if ticker.upper() in members: return sector
    return "ALTCOINS / OTROS"

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

def find_last_signal_audit(df, bear_longs):
    if df.empty or len(df) < 2: return None, None, None, None, False, "-"
    
    last_entry_date, last_entry_px = None, None
    last_exit_date, last_exit_px = None, None
    is_active = False
    verdict = "-"
    
    for i in range(1, len(df)):
        authorized = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_ok = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1] and df['rsi_smooth'].iloc[i] < 50
        
        # LÓGICA DE ENTRADA
        if not is_active and (authorized and ha_flip and macd_accel and rsi_ok):
            is_active = True
            last_entry_date, last_entry_px = df.index[i], df['Close'].iloc[i]
            # Resetear salida porque entramos en una nueva
            last_exit_date, last_exit_px = None, None
        
        # LÓGICA DE SALIDA
        elif is_active and (df['ha_color'].iloc[i] == "Rojo" and df['hist'].iloc[i] < df['hist'].iloc[i-1] and df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]):
            is_active = False
            last_exit_date, last_exit_px = df.index[i], df['Close'].iloc[i]

    # Veredicto dinámico si sigue activa
    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
    
    return last_entry_date, last_entry_px, last_exit_date, last_exit_px, is_active, verdict

# ─────────────────────────────────────────────
# INTERFAZ Y CONECTIVIDAD
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    # Usamos KuCoin Futures para data de perpetuos
    return ccxt.kucoinfutures({'enableRateLimit': True})

def fetch_symbols():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        symbols = [s for s in markets if '/USDT:USDT' in s and markets[s]['active']]
        filtered = [s for s in symbols if not any(x in s for x in ['3L', '3S'])]
        return sorted(filtered)
    except: return []

st.title("🛡️ SLY | CRIPTO SIGNAL AUDITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()

    if "crypto_list" in st.session_state:
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        
        if st.button("🚀 ANALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando 4H: {sym}")
                    raw_data = ex.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    
                    # Llamada al motor de auditoría
                    ent_dt, ent_px, exit_dt, exit_px, vigente, verd = find_last_signal_audit(data, bear_longs)
                    
                    current_close = data['Close'].iloc[-1]
                    
                    # CÁLCULO DE PNL: Si está vigente usa precio actual, si cerró usa precio de salida
                    if vigente:
                        pnl_val = ((current_close - ent_px) / ent_px) * 100
                        status_str = "VIGENTE 🟢"
                    elif ent_px and exit_px:
                        pnl_val = ((exit_px - ent_px) / ent_px) * 100
                        status_str = "CERRADA 🔴"
                    else:
                        pnl_val = 0.0
                        status_str = "SIN SEÑAL ⚪"

                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT:USDT", ""), 
                        "Sector": get_crypto_sector(sym.replace(":USDT","")),
                        "Fecha Entrada": ent_dt.strftime('%d/%m %H:%M') if ent_dt else "-",
                        "Fecha Cierre": exit_dt.strftime('%d/%m %H:%M') if exit_dt else ("-" if vigente else "N/A"),
                        "Estado": status_str,
                        "Resultado %": f"{pnl_val:.2f}%",
                        "Veredicto": verd if vigente else ("OPERACIÓN FINALIZADA" if exit_px else "-"),
                        "Precio Actual": f"{current_close:.4f}",
                        "RSI 4H": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.05)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}
        st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL Y TABLA
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    
    st.subheader("📋 Matriz de Auditoría Cripto 4H")
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "OPERACIÓN FINALIZADA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        if "%" in str_v and "-" not in str_v and "0.00" not in str_v: return 'color: #2E7D32; font-weight: bold;'
        if "%" in str_v and "-" in str_v: return 'color: #B71C1C; font-weight: bold;'
        return ''

    st.dataframe(df_full.style.map(color_cells), use_container_width=True, height=600)
else:
    st.info("👈 Sincronice con KuCoin y analice lotes para ver cierres y ganancias.")
