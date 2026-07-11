import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME (SHORT)
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | SHORT MONITOR 4H")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #B71C1C; font-weight: 800; border-bottom: 3px solid #B71C1C; }
    .stProgress > div > div > div > div { background-color: #B71C1C; }
    .sector-box { background-color: #FFEBEE; padding: 15px; border-radius: 8px; border-left: 5px solid #C62828; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #B71C1C; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results_short" not in st.session_state:
    st.session_state["master_results_short"] = {}

# ─────────────────────────────────────────────
# MAPEO SECTORIAL CRIPTO
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC/USDT", "ETH/USDT"],
    "LAYER 1": ["SOL/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "NEAR/USDT", "FTM/USDT"],
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
# MOTORES TÉCNICOS SLY (4H) - INVERSIÓN DE LÓGICA
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

def find_last_short_signal(df, bull_shorts):
    if df.empty or len(df) < 2: return None, None, False, "-"
    last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
    
    for i in range(1, len(df)):
        # 1. Filtro de Régimen: EMA 52 por debajo de EMA 260 (Bearish)
        authorized = (df['ema52'].iloc[i] < df['ema260'].iloc[i]) or bull_shorts
        
        # 2. Gatillo de Entrada Short: HA Verde a Rojo + MACD Perdiendo fuerza alcista + RSI bajando + RSI > 50
        ha_flip_red = df['ha_color'].iloc[i] == "Rojo" and df['ha_color'].iloc[i-1] == "Verde"
        macd_dropping = df['hist'].iloc[i] < df['hist'].iloc[i-1]
        rsi_dropping = df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]
        rsi_premium = df['rsi_smooth'].iloc[i] > 50 # Zona de Short (Premium)
        
        if not is_active and (authorized and ha_flip_red and macd_dropping and rsi_dropping and rsi_premium):
            is_active, last_entry_date, last_entry_px = True, df.index[i], df['Close'].iloc[i]
        
        # 3. Gatillo de Salida Short: HA Verde + MACD subiendo + RSI subiendo
        elif is_active and (df['ha_color'].iloc[i] == "Verde" and df['hist'].iloc[i] > df['hist'].iloc[i-1] and df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1]):
            is_active = False

    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        # Cruce de 0 desde abajo hacia arriba (Liquidación de Short)
        if p_h < 0 and c_h >= 0: verdict = "CERRAR OPERACIÓN 🟢"
        # Mantener: El histograma sigue cayendo (ganando fuerza bajista)
        elif c_h < p_h: verdict = "MANTENER 🔴"
        # Pierde fuerza: El histograma empieza a subir (acercándose a 0 desde abajo)
        else: verdict = "PIERDE FUERZA 🟡"
        
    return last_entry_date, last_entry_px, is_active, verdict

# ─────────────────────────────────────────────
# CONECTIVIDAD KUCOIN
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

st.title("🛡️ SLY | CRIPTO SHORT MONITOR 4H")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()

    if "crypto_list" in st.session_state:
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bull_shorts = st.checkbox("Habilitar Bull-Shorts (Operar cortos en tendencia alcista)", value=False)
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando 4H (SHORT): {sym}")
                    raw_data = ex.fetch_ohlcv(sym, timeframe='4h', limit=1000)
                    df = pd.DataFrame(raw_data, columns=['time','open','high','low','close','vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    data = get_sly_indicators(df)
                    if data.empty: continue
                    
                    sig_date, sig_px, vigente, verd = find_last_short_signal(data, bull_shorts)
                    
                    # Cálculo PnL para SHORT: (Entrada - Actual) / Entrada
                    pnl_val = f"{((sig_px - data['Close'].iloc[-1]) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    
                    st.session_state["master_results_short"][sym] = {
                        "Activo": sym.replace("/USDT", ""), 
                        "Sector": get_crypto_sector(sym),
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": "VIGENTE 🔴" if vigente else "CERRADA ⚪",
                        "PnL Real": pnl_val,
                        "Veredicto": verd,
                        "Precio": f"{data['Close'].iloc[-1]:.4f}",
                        "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                        "Régimen": "BAJISTA" if data['ema52'].iloc[-1] < data['ema260'].iloc[-1] else "ALCISTA"
                    }
                    time.sleep(0.1)
                except: continue
            st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_short"] = {}
        st.rerun()

# ─────────────────────────────────────────────
# RESUMEN SECTORIAL
# ─────────────────────────────────────────────
if st.session_state["master_results_short"]:
    df_full = pd.DataFrame(st.session_state["master_results_short"].values())
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🔴"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN SHORT (VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="sector-box">
                    <div class="sector-title">{row['Sector']}: {len(row['Activo'])} Cortos</div>
                    <div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div>
                </div>
                """, unsafe_allow_html=True)
    else: st.warning("Sin posiciones de SHORT abiertas.")

    st.subheader("📋 Matriz de Señales SHORT 4H")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells_short(val):
        str_v = str(val)
        if "VIGENTE 🔴" in str_v or "MANTENER 🔴" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "CERRADA ⚪" in str_v or "CERRAR OPERACIÓN 🟢" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells_short), use_container_width=True, height=600)
else:
    st.info("👈 Sincronice y analice lotes para detectar oportunidades de SHORT.")
