import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE SEGURIDAD (CONTRASEÑA)
# ─────────────────────────────────────────────
PASSWORD_MAESTRA = "SLY2026" 

def check_password():
    if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 ACCESO RESTRINGIDO | SLY CRIPTO ENGINE")
        input_pass = st.text_input("Credencial de Operador:", type="password")
        if st.button("Desbloquear Sistema"):
            if input_pass == PASSWORD_MAESTRA:
                st.session_state["authenticated"] = True; st.rerun()
            else:
                st.error("❌ Credencial Incorrecta. Acceso Denegado.")
        return False
    return True

if check_password():
    # ─────────────────────────────────────────────
    # CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME
    # ─────────────────────────────────────────────
    st.set_page_config(layout="wide", page_title="SLY | CRIPTO MONITOR V1.1")

    st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; color: #1C1E21; }
        .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
        h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #004D40; }
        .stProgress > div > div > div > div { background-color: #004D40; }
        section[data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E0E0E0; }
        .sector-box { background-color: #F1F8E9; padding: 15px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        .sector-title { font-weight: bold; color: #1B5E20; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

    if "master_results_crypto" not in st.session_state:
        st.session_state["master_results_crypto"] = {}
    if "all_crypto_symbols" not in st.session_state:
        st.session_state["all_crypto_symbols"] = []

    # ─────────────────────────────────────────────
    # MAPEO SECTORIAL CRIPTO
    # ─────────────────────────────────────────────
    CRYPTO_SECTOR_MAP = {
        "BITCOIN": ["BTC/USDT", "BTC"],
        "ETHEREUM": ["ETH/USDT", "ETH"],
        "MAJOR ALTS": ["SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "TRX/USDT"],
        "LAYER 2 / DEFI": ["ARB/USDT", "OP/USDT", "UNI/USDT", "LINK/USDT", "AAVE/USDT", "LDO/USDT", "MKR/USDT"],
        "AI / MEME": ["RNDR/USDT", "FET/USDT", "PEPE/USDT", "SHIB/USDT", "BONK/USDT", "WIF/USDT", "FLOKI/USDT"]
    }

    def get_crypto_sector(symbol):
        clean_sym = symbol.replace("/USDT", "").replace(":USDT", "").upper()
        for sector, members in CRYPTO_SECTOR_MAP.items():
            if clean_sym in [m.upper() for m in members]: return sector
        return "OTROS / DEGEN"

    # ─────────────────────────────────────────────
    # MOTORES TÉCNICOS SLY
    # ─────────────────────────────────────────────
    def get_sly_indicators(df):
        try:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
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

    def find_last_signal_1D(df, bear_longs):
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

    @st.cache_resource
    def get_exchange():
        return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

    @st.cache_data(ttl=300)
    def get_active_crypto_symbols(min_vol):
        try:
            ex = get_exchange()
            tickers = ex.fetch_tickers()
            valid = []
            for s, t in tickers.items():
                if "/USDT" in s and not any(ss in s for ss in ["USDC", "DAI", "TUSD", "FDUSD"]): 
                    vol = t.get("quoteVolume", 0)
                    if vol >= min_vol: valid.append(s)
            return sorted(valid)
        except: return []

    def analyze_single_crypto(symbol, exchange, bear_longs):
        ohlcv_1D = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=500)
        df_1D = pd.DataFrame(ohlcv_1D, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df_1D['dt'] = pd.to_datetime(df_1D['time'], unit='ms')
        df_1D.set_index('dt', inplace=True)
        df_ind = get_sly_indicators(df_1D)
        if df_ind.empty: return None

        sig_date, sig_px, vigente, verd = find_last_signal_1D(df_ind, bear_longs)
        
        # PnL Dinámico (Solo si vigente)
        pnl_str = f"{((df_ind['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
        
        row = {
            "Activo": symbol.replace("/USDT", ""), "Sector": get_crypto_sector(symbol),
            "Última Señal": sig_date.strftime('%Y-%m-%d') if sig_date else "-",
            "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
            "PnL Real": pnl_str, "Veredicto": verd, "Precio": round(df_ind['Close'].iloc[-1], 4),
            "RSI 1D": round(df_ind['rsi_smooth'].iloc[-1], 1),
            "Régimen": "ALCISTA" if df_ind['ema52'].iloc[-1] > df_ind['ema260'].iloc[-1] else "BAJISTA"
        }
        return row

    # ─────────────────────────────────────────────
    # INTERFAZ
    # ─────────────────────────────────────────────
    st.title("🛡️ SLY | CRIPTO SIGNAL MONITOR V1.1")

    with st.sidebar:
        st.header("⚙️ Radar Ops")
        min_vol = st.number_input("Volumen Mín 24h:", value=5000000)
        if st.button("📡 1. SINCRONIZAR"):
            st.session_state["all_crypto_symbols"] = get_active_crypto_symbols(min_vol)
            st.rerun()

        if st.session_state["all_crypto_symbols"]:
            batch_size = st.number_input("Lote:", 10, 100, 30)
            total_lotes = (len(st.session_state["all_crypto_symbols"]) // batch_size) + 1
            batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
            bear_longs = st.checkbox("Bear-Longs", value=True)
            
            if st.button("🚀 2. ACTUALIZAR Y ACUMULAR"):
                exchange = get_exchange() # DEFINICIÓN CORRECTA
                subset = st.session_state["all_crypto_symbols"][batch_idx*batch_size : (batch_idx+1)*batch_size]
                prog = st.progress(0)
                for i, sym in enumerate(subset):
                    prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                    try:
                        res = analyze_single_crypto(sym, exchange, bear_longs)
                        if res: st.session_state["master_results_crypto"][sym] = res
                    except: continue
                    time.sleep(exchange.rateLimit / 1000) # FIX: exchange en lugar de ex
                st.rerun()

        if st.button("🗑️ Limpiar Memoria"):
            st.session_state["master_results_crypto"] = {}; st.rerun()
        if st.button("🔒 Cerrar Sesión"): 
            st.session_state["authenticated"] = False; st.rerun()

    # ─────────────────────────────────────────────
    # RESUMEN Y MATRIZ
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
                    st.markdown(f"<div class='sector-box'><div class='sector-title'>{row['Sector']}: {len(row['Activo'])}</div><div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
        
        st.subheader("📋 Matriz Cripto")
        df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
        
        def color_cells(val):
            str_v = str(val)
            if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
            if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
            return ''

        st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
    else: st.info("Sincronice e inicie el escaneo.")
