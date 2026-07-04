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
# >>> CAMBIA ESTA CONTRASEÑA <<<
PASSWORD_MAESTRA = "SLY2026" 

def check_password():
    if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 ACCESO RESTRINGIDO | SLY CRIPTO ENGINE")
        input_pass = st.text_input("Credencial de Operador:", type="password")
        if st.button("Desbloquear Sistema"):
            if input_pass == PASSWORD_MAESTRA:
                st.session_state["authenticated"] = True; st.rerun()
            else: st.error("❌ Credencial Incorrecta. Acceso Denegado.")
        return False
    return True

if check_password(): # Todo el script se ejecuta solo si la contraseña es correcta
    # ─────────────────────────────────────────────
    # CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME (CRIPTO)
    # ─────────────────────────────────────────────
    st.set_page_config(layout="wide", page_title="SLY | CRIPTO MONITOR V1.0")

    st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; color: #1C1E21; }
        .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
        h1 { color: #F3BA2F; font-weight: 800; border-bottom: 3px solid #F3BA2F; } /* Binance Yellow */
        .stProgress > div > div > div > div { background-color: #F3BA2F; }
        section[data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E0E0E0; }
        .sector-box { background-color: #FFF3E0; padding: 15px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); } /* Crypto Orange */
        .sector-title { font-weight: bold; color: #BF360C; font-size: 1.1em; } /* Crypto Dark Orange */
    </style>
    """, unsafe_allow_html=True)

    if "master_results_crypto" not in st.session_state:
        st.session_state["master_results_crypto"] = {}
    if "all_crypto_symbols" not in st.session_state:
        st.session_state["all_crypto_symbols"] = []

    # ─────────────────────────────────────────────
    # MAPEO SECTORIAL CRIPTO (EJEMPLO)
    # ─────────────────────────────────────────────
    CRYPTO_SECTOR_MAP = {
        "BITCOIN": ["BTC/USDT", "BTC"],
        "ETHEREUM": ["ETH/USDT", "ETH"],
        "MAJOR ALTS": ["SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT"],
        "LAYER 2 / DEFI": ["ARB/USDT", "OP/USDT", "UNI/USDT", "LINK/USDT", "AAVE/USDT"],
        "MEME COINS": ["SHIB/USDT", "PEPE/USDT"],
        "BLOCKCHAIN EQUITY": ["MSTR", "COIN", "MARA", "RIOT"] # Acciones relacionadas
    }

    def get_crypto_sector(symbol):
        clean_sym = symbol.replace("/USDT", "").replace(":USDT", "").upper()
        for sector, members in CRYPTO_SECTOR_MAP.items():
            if clean_sym in [m.upper() for m in members]: return sector
        return "OTROS / DEGEN"

    # ─────────────────────────────────────────────
    # MOTOR DE CÁLCULO ZERO-LAG (DEMA)
    # ─────────────────────────────────────────────
    def get_sly_indicators(df):
        try:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_levels[0] # Changed to get_level_levels[0]
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}) # CCXT uses lowercase
            df = df.dropna(subset=['Close'])

            def dema(s, length):
                ema1 = s.ewm(span=length, adjust=False).mean()
                ema2 = ema1.ewm(span=length, adjust=False).mean()
                return 2 * ema1 - ema2

            df['macd_line'] = dema(df['Close'], 12) - dema(df['Close'], 26)
            df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
            df['hist'] = df['macd_line'] - df['signal_line']
            df['rsi_smooth'] = dema(ta.rsi(df['Close'], length=14).fillna(50), 5)
            
            # Heikin Ashi Recursivo
            ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
            ha_o = np.zeros(len(df))
            ha_o[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
            for i in range(1, len(df)): ha_o[i] = (ha_o[i-1] + ha_c.iloc[i-1]) / 2
            df['ha_color'] = np.where(ha_c > ha_o, "Verde", "Rojo")
            
            # EMAs de Régimen
            df['ema52'] = ta.ema(df['Close'], length=52)
            df['ema260'] = ta.ema(df['Close'], length=260)
            
            return df.dropna(subset=['ema260'])
        except Exception as e:
            st.warning(f"Error en indicadores para DF: {e}")
            return pd.DataFrame()

    # ─────────────────────────────────────────────
    # MÁQUINA DE ESTADOS (BASE PARA 1D MACRO)
    # ─────────────────────────────────────────────
    def find_last_signal_1D(df_1D, bear_longs):
        if df_1D.empty or len(df_1D) < 2: return None, None, False, "-"
        
        last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
        
        # Recorrido de toda la historia del 1D para encontrar la señal
        for i in range(1, len(df_1D)):
            # 1. Filtro de Régimen (EMA 52/260 en 1D)
            trend_bull = df_1D['ema52'].iloc[i] > df_1D['ema260'].iloc[i]
            authorized = trend_bull or bear_longs
            
            # 2. Condiciones de Entrada (LONG ONLY)
            ha_flip = df_1D['ha_color'].iloc[i] == "Verde" and df_1D['ha_color'].iloc[i-1] == "Rojo"
            macd_accel = df_1D['hist'].iloc[i] > df_1D['hist'].iloc[i-1]
            rsi_rising = df_1D['rsi_smooth'].iloc[i] > df_1D['rsi_smooth'].iloc[i-1]
            rsi_discount = df_1D['rsi_smooth'].iloc[i] < 50
            
            entry_trigger = authorized and ha_flip and macd_accel and rsi_rising and rsi_discount
            
            # 3. Condiciones de Salida
            exit_trigger = (df_1D['ha_color'].iloc[i] == "Rojo" and 
                            df_1D['hist'].iloc[i] < df_1D['hist'].iloc[i-1] and 
                            df_1D['rsi_smooth'].iloc[i] < df_1D['rsi_smooth'].iloc[i-1])

            if not is_active and entry_trigger:
                is_active = True
                last_entry_date = df_1D.index[i]
                last_entry_px = df_1D['Close'].iloc[i]
            elif is_active and exit_trigger:
                is_active = False

        # Veredicto para la vela actual (si la posición está activa)
        if is_active:
            curr_h = df_1D['hist'].iloc[-1]
            prev_h = df_1D['hist'].iloc[-2]
            if prev_h > 0 and curr_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
            elif curr_h > prev_h: verdict = "MANTENER 🟢"
            else: verdict = "PIERDE FUERZA 🟡"

        return last_entry_date, last_entry_px, is_active, verdict

    # ─────────────────────────────────────────────
    # MOTOR DE DATOS CCXT
    # ─────────────────────────────────────────────
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
                # Filtramos por pares USDT que no sean stablecoins principales o fiat
                if "/USDT" in s and not any(ss in s for ss in ["USDC", "DAI", "TUSD", "FDUSD"]): 
                    vol = t.get("quoteVolume", 0)
                    if vol >= min_vol:
                        valid.append(s)
            return sorted(valid)
        except Exception as e:
            st.error(f"Error al sincronizar tickers: {e}. Revise API Keys o conexión.")
            return []

    # ─────────────────────────────────────────────
    # ANALISIS DE UN ACTIVO CRIPTO (Loop principal)
    # ─────────────────────────────────────────────
    def analyze_single_crypto(symbol, exchange, bear_longs):
        row = {"Activo": symbol.replace("/USDT", ""), "Sector": get_crypto_sector(symbol)}
        
        # 1. Obtener datos 1D para la señal principal y régimen
        ohlcv_1D = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=500) # Suficiente para EMA260 en 1D
        df_1D = pd.DataFrame(ohlcv_1D, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df_1D['dt'] = pd.to_datetime(df_1D['time'], unit='ms')
        df_1D.set_index('dt', inplace=True)
        
        df_1D_ind = get_sly_indicators(df_1D.copy())
        if df_1D_ind.empty: return None

        # Señal principal (Estado, Veredicto, PnL) basada en 1D
        sig_date_1D, sig_px_1D, is_active_1D, verdict_1D = find_last_signal_1D(df_1D_ind, bear_longs)
        
        current_close = df_1D_ind['Close'].iloc[-1]
        pnl_str = f"{((current_close - sig_px_1D) / sig_px_1D * 100):.2f}%" if (is_active_1D and sig_px_1D) else "-"
        
        row.update({
            "Última Señal (1D)": sig_date_1D.strftime('%Y-%m-%d') if sig_date_1D else "-",
            "Estado (1D)": "VIGENTE 🟢" if is_active_1D else "CERRADA 🔴",
            "PnL Real (1D)": pnl_str,
            "Veredicto (1D)": verdict_1D,
            "Precio": round(current_close, 4), # Más decimales para cripto
            "Régimen (1D)": "ALCISTA" if df_1D_ind['ema52'].iloc[-1] > df_1D_ind['ema260'].iloc[-1] else "BAJISTA"
        })

        # 2. Obtener datos de contexto para 4H y 1H
        for tf_label, tf_interval in {"4H": "4h", "1H": "1h"}.items():
            ohlcv_context = exchange.fetch_ohlcv(symbol, timeframe=tf_interval, limit=100) # 100 velas es suficiente para MACD/RSI
            df_context = pd.DataFrame(ohlcv_context, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df_context['dt'] = pd.to_datetime(df_context['time'], unit='ms')
            df_context.set_index('dt', inplace=True)
            
            df_context_ind = get_sly_indicators(df_context.copy())
            if df_context_ind.empty: continue

            # Extraer solo MACD Hist y RSI para contexto
            row[f"MACD Hist ({tf_label})"] = "Subiendo 📈" if df_context_ind['hist'].iloc[-1] > df_context_ind['hist'].iloc[-2] else "Bajando 📉"
            row[f"RSI ({tf_label})"] = f"{df_context_ind['rsi_smooth'].iloc[-1]:.1f} {'Subiendo' if df_context_ind['rsi_smooth'].iloc[-1] > df_context_ind['rsi_smooth'].iloc[-2] else 'Bajando'}"

        return row
    
    # ─────────────────────────────────────────────
    # INTERFAZ DE USUARIO
    # ─────────────────────────────────────────────
    st.title("🛡️ SLY | CRIPTO SIGNAL MONITOR V1.0")

    with st.sidebar:
        st.header("⚙️ Crypto Radar Ops")
        min_vol = st.number_input("Volumen Mínimo 24h (USDT):", value=5000000, step=1000000)
        
        if st.button("📡 1. SINCRONIZAR MERCADO", type="primary", use_container_width=True):
            st.session_state["all_crypto_symbols"] = get_active_crypto_symbols(min_vol)
            st.rerun()

        if st.session_state["all_crypto_symbols"]:
            total_symbols = len(st.session_state["all_crypto_symbols"])
            st.success(f"Activos filtrados: {total_symbols}")
            
            batch_size = st.number_input("Activos por Lote:", 10, 50, 25) # Menos por la volatilidad de CCXT
            total_lotes = (total_symbols // batch_size) + (1 if total_symbols % batch_size > 0 else 0)
            batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
            bear_longs = st.checkbox("Habilitar Bear-Longs (1D)", value=True)
            
            if st.button("🚀 2. INICIAR ESCANEO Y ACUMULAR", type="secondary", use_container_width=True):
                exchange = get_exchange()
                subset = st.session_state["all_crypto_symbols"][batch_idx*batch_size : (batch_idx+1)*batch_size]
                prog = st.progress(0)
                
                for i, sym in enumerate(subset):
                    prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                    try:
                        result_row = analyze_single_crypto(sym, exchange, bear_longs)
                        if result_row:
                            st.session_state["master_results_crypto"][sym] = result_row
                    except Exception as e:
                        st.warning(f"Error procesando {sym}: {e}")
                    time.sleep(ex.rateLimit / 1000) # Respetar rate limits del exchange

                st.rerun() # Actualiza la tabla después de procesar el lote

        st.divider()
        if st.button("🗑️ Limpiar Memoria"):
            st.session_state["master_results_crypto"] = {}; st.session_state["all_crypto_symbols"] = []; st.rerun()
        if st.button("🔒 Cerrar Sesión"): 
            st.session_state["authenticated"] = False; st.rerun()

    # ─────────────────────────────────────────────
    # RENDERIZADO ACUMULATIVO Y RESUMEN
    # ─────────────────────────────────────────────
    if st.session_state["master_results_crypto"]:
        df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
        df_vigentes = df_full[df_full["Estado (1D)"] == "VIGENTE 🟢"]

        st.subheader("📊 RESUMEN DE EXPOSICIÓN (VIGENTES POR SECTOR)")
        if not df_vigentes.empty:
            summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
            cols = st.columns(3)
            for idx, row in summary.iterrows():
                with cols[idx % 3]:
                    st.markdown(f"<div class='sector-box'><div class='sector-title'>{row['Sector']}: {len(row['Activo'])}</div><div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
        else: st.warning("Sin posiciones VIGENTES en los activos analizados.")

        st.subheader("📋 Matriz de Señales Cripto")
        df_res = df_full.sort_values(by=["Estado (1D)", "Activo"], ascending=[False, True])
        
        def color_cells(val):
            str_v = str(val)
            if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v or "Subiendo" in str_v or "📈" in str_v: 
                return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
            if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v or "Bajando" in str_v or "📉" in str_v: 
                return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
            if "PIERDE" in str_v: 
                return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
            return ''

        st.dataframe(
            df_res.style.map(color_cells), 
            use_container_width=True, 
            height=600,
            column_config={
                "PnL Real (1D)": st.column_config.TextColumn(format="%s"), # Formato como texto porque ya lleva %
                "Precio": st.column_config.NumberColumn(format="$%.4f")
            }
        )
    else: st.info("Sincronice el mercado y cargue lotes para iniciar el monitoreo de señales Cripto.")
