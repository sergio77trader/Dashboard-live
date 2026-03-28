import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN DE INTERFAZ (ESTILO BINANCE)
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | BINANCE ALPHA TERMINAL")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #F3BA2F; font-weight: 800; text-shadow: 1px 1px 2px #000; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #F3BA2F; color: #1e1e1e; border: none; }
    .status-msg { padding: 15px; border-radius: 10px; background-color: #fff9e6; color: #856404; margin-bottom: 20px; border: 1px solid #ffeeba; }
    .stDataFrame { border: 1px solid #F3BA2F; }
</style>
""", unsafe_allow_html=True)

# --- LISTA MAESTRA DE COBERTURA TOTAL (~500 COINS) ---
BINANCE_WHITELIST = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'LINK', 'MATIC', 'SHIB', 'TRX', 'LTC', 'BCH', 'UNI', 'NEAR', 'SUI', 'APT', 'OP', 'ARB', 'TIA', 'INJ', 'FET', 'RNDR', 'STX', 'KAS', 'ORDI', 'FIL', 'ATOM', 'IMX', 'HBAR', 'LDO', 'ICP', 'GRT', 'AAVE', 'MKR', 'RUNE', 'EGLD', 'SEI', 'PEPE', 'WIF', 'FLOKI', 'BONK', 'JUP', 'PYTH', 'ENA', 'BOME', 'STRK', 'DYDX', 'GALA', 'ALGO', 'FLOW', 'VET', 'AXS', 'SAND', 'MANA', 'THETA', 'CHZ', 'BEAM', 'PENDLE', 'ALT', 'MANTA', 'PIXEL', 'DYM', 'RON', 'ARKM', 'ID', 'MAV', 'WOO', 'JTO', 'SATS', 'RATS', 'MYRO', 'METIS', 'GNO', 'ENS', 'ASTR', 'WLD', 'ZETA', 'XAI', 'TAO', 'TON', 'NOT', 'TURBO', 'MEME', 'LISTA', 'IO', 'ZK', 'ZRO', 'BANANA', 'RENDER', 'FIDA', 'EIGEN', 'SCR', 'COW', 'CETUS', 'PNUT', 'ACT', 'NEIRO', 'MOODENG', 'THE', 'VANA', 'PENGU', 'VTHO', 'ONG', 'GAS', 'NEO', 'QTUM', 'XMR', 'ZEC', 'DASH', 'LRC', 'OMG', 'ZIL', 'KNC', 'KAVA', 'BAND', 'IOST', 'CKB', 'STMX', 'ANKR', 'REN', 'CRV', 'SUSHI', 'COMP', 'SNX', 'UMA', 'YFI', 'BAL', 'SRM', 'ALPHA', 'BEL', 'WING', 'FLM', 'SUN', 'JST', 'OG', 'ASR', 'ATM', 'ACM', 'PSG', 'BAR', 'REI', 'OXT', 'SXP', 'KMD', 'NMR', 'DGB', 'LSK', 'WAVES', 'MTL', 'AR', 'BLZ', 'STORJ', 'SC', 'RLC']

if "accumulated_data" not in st.session_state:
    st.session_state["accumulated_data"] = pd.DataFrame()
if "filtered_symbols" not in st.session_state:
    st.session_state["filtered_symbols"] = []
if "current_pointer" not in st.session_state:
    st.session_state["current_pointer"] = 0

# ─────────────────────────────────────────────
# 2. MOTOR TÉCNICO SLY (RECURSIVO MANUAL)
# ─────────────────────────────────────────────
def run_sly_engine_1d(df):
    if df.empty or len(df) < 35: return "FUERA ⚪", "-", "-"
    
    # MACD
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    
    # Heikin Ashi Manual (Evita repainting)
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    # Máquina de Estados
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev = hist.iloc[i], hist.iloc[i-1]
        hd, hd_prev = ha_dir[i], ha_dir[i-1]
        
        longC = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shrtC = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        
        if longC: state, entry_px, entry_tm = 1, df['close'].iloc[i], df['dt'].iloc[i]
        elif shrtC: state, entry_px, entry_tm = -1, df['close'].iloc[i], df['dt'].iloc[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
                
    if state != 0:
        pnl = (df['close'].iloc[-1] - entry_px) / entry_px * 100 if state == 1 else (entry_px - df['close'].iloc[-1]) / entry_px * 100
        return ("LONG 🟢" if state == 1 else "SHORT 🔴"), entry_tm.strftime("%d/%m/%y"), f"{pnl:+.2f}%"
    return "FUERA ⚪", "-", "-"

# ─────────────────────────────────────────────
# 3. MOTOR DE DATOS (KUCOIN CON FILTRO DE UNICIDAD)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 30000})

def fetch_universe():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        compatible = []
        seen_bases = set() # Para evitar duplicados de Spot vs Futuros
        
        for s in markets:
            if '/USDT' not in s: continue
            base = s.split('/')[0]
            if base in seen_bases: continue # Si ya tenemos el BTC, no tomamos el BTC:USDT
            
            if markets[s].get('active', True):
                vol = markets[s].get('quoteVolume', 0)
                if base in BINANCE_WHITELIST or vol > 300000:
                    compatible.append(s)
                    seen_bases.add(base)
                    
        return sorted(list(set(compatible)))
    except: return []

def get_recommendation(delta):
    if delta > 4: return "🚀 ALPHA STRIKE"
    if delta > 1: return "🏃 CORREDOR"
    if delta > -1: return "⚖️ NEUTRAL"
    return "🐢 LENTO"

# ─────────────────────────────────────────────
# 4. INTERFAZ Y ESCANEO
# ─────────────────────────────────────────────
st.title("🛡️ SLY Alpha Terminal v3.2")
st.markdown('<div class="status-msg">Estado: <b>Limpieza de duplicados activa</b>. Analizando paridad Cripto/BTC + Señal 1D.</div>', unsafe_allow_html=True)

if not st.session_state["filtered_symbols"]:
    if st.button("📡 1. SINCRONIZAR UNIVERSO UNIFICADO"):
        st.session_state["filtered_symbols"] = fetch_universe()
        st.rerun()

if st.session_state["filtered_symbols"]:
    total_assets = len(st.session_state["filtered_symbols"])
    pointer = st.session_state["current_pointer"]
    batch_size = st.selectbox("Lote de escaneo:", [25, 50, 100], index=1)
    next_limit = min(pointer + batch_size, total_assets)
    
    if pointer < total_assets:
        if st.button(f"🚀 ESCANEAR BLOQUE: {pointer} al {next_limit}"):
            ex = get_exchange()
            targets = st.session_state["filtered_symbols"][pointer:next_limit]
            
            btc_t = ex.fetch_ticker('BTC/USDT')
            btc_perf = btc_t.get('percentage', 0)
            
            new_rows = []
            prog = st.progress(0)
            for i, sym in enumerate(targets):
                try:
                    # Usamos limit=100 para asegurar convergencia del motor SLY
                    ohlcv = ex.fetch_ohlcv(sym, timeframe='1d', limit=100)
                    df = pd.DataFrame(ohlcv, columns=['t','open','high','low','close','v'])
                    df['dt'] = pd.to_datetime(df['t'], unit='ms')
                    
                    alt_perf = ((df['close'].iloc[-1] / df['close'].iloc[-2]) - 1) * 100
                    delta = alt_perf - btc_perf
                    sig, fecha, pnl = run_sly_engine_1d(df)
                    
                    # Limpiamos el nombre para que diga solo "CHZ" y no "CHZ:USDT"
                    clean_name = sym.split('/')[0]
                    
                    new_rows.append({
                        "Activo": clean_name,
                        "RECOMENDACIÓN": get_recommendation(delta),
                        "Precio": float(df['close'].iloc[-1]),
                        "Rend. 24h": f"{alt_perf:+.2f}%",
                        "Vs BTC (Delta)": round(float(delta), 2),
                        "1D Signal": sig,
                        "1D Fecha": fecha,
                        "1D PnL": pnl
                    })
                except: continue
                prog.progress((i + 1) / len(targets))
            
            if new_rows:
                df_new = pd.DataFrame(new_rows)
                # Concatenar y eliminar duplicados finales por si acaso
                st.session_state["accumulated_data"] = pd.concat([st.session_state["accumulated_data"], df_new]).drop_duplicates(subset="Activo", keep="last")
                st.session_state["current_pointer"] = next_limit
                st.rerun()

# ─────────────────────────────────────────────
# 5. RENDERIZADO CON FORMATO ORIGINAL Y COLORES
# ─────────────────────────────────────────────
if not st.session_state["accumulated_data"].empty:
    st.divider()
    df_disp = st.session_state["accumulated_data"].sort_values(by="Vs BTC (Delta)", ascending=False).reset_index(drop=True)

    def style_output(row):
        styles = [''] * len(row)
        # Colores para Delta
        try:
            delta_val = float(row["Vs BTC (Delta)"])
            if delta_val > 0: styles[row.index.get_loc("Vs BTC (Delta)")] = 'color: #1b5e20; font-weight: bold;'
            elif delta_val < 0: styles[row.index.get_loc("Vs BTC (Delta)")] = 'color: #b71c1c; font-weight: bold;'
        except: pass

        # Colores para Señal SLY (Fondo completo para la celda)
        sig_val = str(row["1D Signal"])
        if "LONG" in sig_val: styles[row.index.get_loc("1D Signal")] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif "SHORT" in sig_val: styles[row.index.get_loc("1D Signal")] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        
        # Colores para PnL
        pnl_val = str(row["1D PnL"])
        if "%" in pnl_val:
            try:
                v = float(pnl_val.replace("%",""))
                styles[row.index.get_loc("1D PnL")] = f'color: {"#1b5e20" if v >= 0 else "#b71c1c"}; font-weight: bold;'
            except: pass
            
        return styles

    st.dataframe(df_disp.style.apply(style_output, axis=1), use_container_width=True, height=600)

    if st.button("🗑️ REINICIAR RADAR"):
        st.session_state["accumulated_data"] = pd.DataFrame()
        st.session_state["current_pointer"] = 0
        st.rerun()
