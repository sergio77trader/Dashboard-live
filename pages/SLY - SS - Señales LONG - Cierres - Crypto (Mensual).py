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
st.set_page_config(layout="wide", page_title="SLY | CRIPTO MULTI-TF MONITOR")

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

# Mapeo de temporalidades para CCXT
TF_OPTIONS = {
    "30 MIN": "30m",
    "1 HS": "1h",
    "4 HS": "4h",
    "1 DIA": "1d",
    "1 SEMANA": "1w",
    "1 MES": "1M"
}

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
# MOTORES TÉCNICOS SLY
# ─────────────────────────────────────────────
def dema(s, length):
    ema1 = s.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    return 2 * ema1 - ema2

def get_sly_indicators(df):
    try:
        df.columns = [c.capitalize() for c in df.columns]
        df = df.dropna(subset=['Close'])

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

# NUEVA FUNCIÓN: Analizar fuerza MACD Mensual
def get_monthly_macd_force(ex, symbol):
    try:
        # Pedimos pocas velas (50 son suficientes para MACD estable)
        raw = ex.fetch_ohlcv(symbol, timeframe='1M', limit=50)
        df = pd.DataFrame(raw, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        m_macd = dema(df['close'], 12) - dema(df['close'], 26)
        m_signal = m_macd.ewm(span=9, adjust=False).mean()
        m_hist = m_macd - m_signal
        
        current_h = m_hist.iloc[-1]
        previous_h = m_hist.iloc[-2]
        
        if current_h > previous_h:
            return "GANANDO FUERZA 📈"
        else:
            return "PERDIENDO FUERZA 📉"
    except:
        return "N/A"

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
# INTERFAZ Y CONECTIVIDAD KUCOIN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({'enableRateLimit': True})

def fetch_symbols():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        symbols = [s for s in markets if '/USDT' in s and markets[s]['active']]
        filtered = [s for s in symbols if not any(x in s for x in ['3L', '3S', 'USDC', 'DAI', 'PAX', 'TUSD'])]
        return sorted(filtered)
    except: return []

st.title(f"🛡️ SLY | CRIPTO SIGNAL TRACKER")

with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("1. Parámetros de Tiempo")
    selected_tf_label = st.selectbox("Seleccionar Temporalidad:", list(TF_OPTIONS.keys()), index=2) 
    selected_tf_code = TF_OPTIONS[selected_tf_label]
    
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()

    if "crypto_list" in st.session_state:
        st.subheader("2. Ejecución")
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando {selected_tf_label}: {sym}")
                    
                    # Temporalidad principal
                    raw_data = ex.fetch_ohlcv(sym, timeframe=selected_tf_code, limit=1000)
                    df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    
                    # Análisis MACD Mensual (Nueva columna)
                    monthly_force = get_monthly_macd_force(ex, sym)
                    
                    sig_date, sig_px, vigente, verd = find_last_signal(data, bear_longs)
                    pnl_val = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    last_rsi = data['rsi_smooth'].iloc[-1]
                    rsi_zone = "SOBRE 50 🟢" if last_rsi > 50 else "BAJO 50 🔴"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", ""), 
                        "Temporalidad": selected_tf_label,
                        "Sector": get_crypto_sector(sym),
                        "MACD Mensual": monthly_force, # AGREGADO
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                        "PnL Real": pnl_val,
                        "Zona RSI": rsi_zone,
                        "Veredicto": verd,
                        "Precio": f"{data['Close'].iloc[-1]:.4f}",
                        "RSI": round(last_rsi, 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                    }
                    time.sleep(0.05)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}
        st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    
    # Reordenar para que MACD Mensual esté al principio
    cols_order = ["Activo", "Sector", "MACD Mensual", "Estado", "Veredicto", "PnL Real", "Última Señal", "Temporalidad", "Zona RSI", "RSI", "Precio", "Régimen"]
    df_full = df_full[cols_order]

    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]

    st.subheader(f"📊 RESUMEN DE EXPOSICIÓN (VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="sector-box">
                    <div class="sector-title">{row['Sector']}: {len(row['Activo'])}</div>
                    <div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div>
                </div>
                """, unsafe_allow_html=True)
    else: st.warning("Sin posiciones abiertas en la temporalidad analizada.")

    st.subheader(f"📋 Matriz de Señales (Filtro Actual: {selected_tf_label})")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v or "SOBRE 50" in str_v or "GANANDO" in str_v: 
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v or "BAJO 50" in str_v or "PERDIENDO" in str_v: 
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE FUERZA" in str_v: 
            return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else:
    st.info("👈 Seleccione temporalidad, sincronice mercado y analice lotes.")
