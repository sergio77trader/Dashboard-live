import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - TITAN DASHBOARD")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #00CC96; }
</style>
""", unsafe_allow_html=True)

# --- MOTOR DE CONEXIÓN (GATE.IO) ---
@st.cache_resource
def get_exchange():
    return ccxt.gate({
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}, # Futuros
        'timeout': 30000
    })

# --- UTILS ---
def safe_rsi(df, len=14):
    if df.empty or len(df) < len: return 50.0
    try:
        val = df.ta.rsi(length=len).iloc[-1]
        return float(val) if not pd.isna(val) else 50.0
    except: return 50.0

def safe_change(curr, prev):
    if prev == 0: return 0.0
    return ((curr - prev) / prev) * 100

@st.cache_data(ttl=600)
def get_targets(limit=10):
    try:
        ex = get_exchange()
        # Gate usa tickers con _ (BTC_USDT)
        tickers = ex.fetch_tickers()
        valid = []
        for s in tickers:
            if '_USDT' in s and tickers[s]['quoteVolume']:
                valid.append({'symbol': s, 'vol': tickers[s]['quoteVolume']})
        
        df = pd.DataFrame(valid).sort_values('vol', ascending=False).head(limit)
        return df['symbol'].tolist()
    except: return ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'DOGE_USDT']

def fetch_titan_data(symbols):
    ex = get_exchange()
    rows = []
    
    prog = st.progress(0, text="Iniciando extracción masiva...")
    total = len(symbols)
    
    for idx, symbol in enumerate(symbols):
        disp_name = symbol.replace('_', '/')
        prog.progress(idx/total, text=f"Procesando {disp_name}...")
        
        row = {'Activo': disp_name}
        
        try:
            # --- 1. DATOS DE PRECIO, RSI Y VOLUMEN (VELAS) ---
            TFS = [
                ('15m', '15m', False, False, True),  # Solo RSI 15m
                ('1H',  '1h',  True,  True,  True),  # Todo
                ('4H',  '4h',  True,  True,  True),  # Todo
                ('12H', '12h', True,  False, True),  # Precio + RSI
                ('1D',  '1d',  True,  True,  True),  # Todo
                ('1W',  '1w',  False, False, True),  # Solo RSI
            ]
            
            current_price = 0.0
            
            for lbl, tf, get_p, get_v, get_r in TFS:
                try:
                    ohlcv = ex.fetch_ohlcv(symbol, timeframe=tf, limit=30)
                    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
                    
                    if not df.empty:
                        close_now = df['close'].iloc[-1]
                        open_prev = df['open'].iloc[-1]
                        
                        if lbl == '1H': current_price = close_now
                        
                        if get_r: row[f'RSI {lbl}'] = safe_rsi(df)
                        
                        if get_p: 
                            chg = safe_change(close_now, open_prev)
                            row[f'P.Chg {lbl}'] = chg / 100 
                            
                        if get_v:
                            vol_usd = df['vol'].iloc[-1] * close_now
                            row[f'Vol {lbl}'] = vol_usd
                except:
                    pass 

            row['Precio ($)'] = current_price

            # --- 2. DATOS DE OPEN INTEREST (FLUJO) ---
            try:
                oi_hist = ex.fetch_open_interest_history(symbol, timeframe='1h', limit=30)
                if oi_hist:
                    df_oi = pd.DataFrame(oi_hist)
                    col = 'openInterestValue' if 'openInterestValue' in df_oi.columns else 'openInterestAmount'
                    if col not in df_oi.columns: col = 'openInterest'
                    
                    vals = df_oi[col].astype(float).values
                    
                    if len(vals) > 0:
                        curr_oi = vals[-1]
                        row['OI Total ($)'] = curr_oi
                        
                        if len(vals) >= 2: row['OI Chg 1H'] = safe_change(curr_oi, vals[-2]) / 100
                        if len(vals) >= 5: row['OI Chg 4H'] = safe_change(curr_oi, vals[-5]) / 100
                        if len(vals) >= 25: row['OI Chg 1D'] = safe_change(curr_oi, vals[-25]) / 100
            except:
                pass 

            rows.append(row)
            
        except Exception:
            continue
            
        time.sleep(0.15)
        
    prog.empty()
    return pd.DataFrame(rows)

# --- UI ---
st.title("🛡️ SystemaTrader: TITAN Dashboard")
st.markdown("### Inteligencia Total: Precio + Volumen + RSI + Open Interest")

with st.sidebar:
    st.header("Configuración")
    LIMIT = st.slider("Cantidad de Activos:", 5, 20, 10)
    
    if st.button("⚡ EJECUTAR TITAN", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- EJECUCIÓN ---
try:
    with st.spinner("Conectando a Matrix (Gate.io)..."):
        targets = get_targets(LIMIT)
        
    if not targets:
        st.error("Error de conexión.")
    else:
        df = fetch_titan_data(targets)
        
        if not df.empty:
            # SANITIZACIÓN CRÍTICA
            df = df.fillna(0.0)
            df = df.replace([np.inf, -np.inf], 0.0)
            
            # --- SECCIÓN 1: ACCIÓN DE PRECIO ---
            st.subheader("1. Estructura de Precio")
            st.dataframe(
                df,
                column_config={
                    "Activo": st.column_config.TextColumn("Crypto", width="small"), # Fixed removido
                    "Precio ($)": st.column_config.NumberColumn("Precio", format="$%.4f"),
                    "P.Chg 1H": st.column_config.NumberColumn("1H %", format="%.2f%%"),
                    "P.Chg 4H": st.column_config.NumberColumn("4H %", format="%.2f%%"),
                    "P.Chg 12H": st.column_config.NumberColumn("12H %", format="%.2f%%"),
                    "P.Chg 1D": st.column_config.NumberColumn("1D %", format="%.2f%%"),
                    "RSI 15m": None, "RSI 1H": None, "RSI 4H": None, "RSI 12H": None, "RSI 1D": None, "RSI 1W": None,
                    "Vol 1H": None, "Vol 4H": None, "Vol 1D": None,
                    "OI Total ($)": None, "OI Chg 1H": None, "OI Chg 4H": None, "OI Chg 1D": None
                },
                use_container_width=True, hide_index=True
            )
            
            st.divider()
            
            # --- SECCIÓN 2: MOMENTUM (RSI) ---
            st.subheader("2. Matriz de Momentum (RSI)")
            st.dataframe(
                df,
                column_config={
                    "Activo": st.column_config.TextColumn("Crypto", width="small"),
                    "RSI 15m": st.column_config.NumberColumn("15m", format="%.0f"),
                    "RSI 1H": st.column_config.NumberColumn("1H", format="%.0f"),
                    "RSI 4H": st.column_config.NumberColumn("4H", format="%.0f"),
                    "RSI 12H": st.column_config.NumberColumn("12H", format="%.0f"),
                    "RSI 1D": st.column_config.NumberColumn("Diario", format="%.0f"),
                    "RSI 1W": st.column_config.NumberColumn("Semanal", format="%.0f"),
                    "Precio ($)": None, "P.Chg 1H": None, "P.Chg 4H": None, "P.Chg 12H": None, "P.Chg 1D": None,
                    "Vol 1H": None, "Vol 4H": None, "Vol 1D": None,
                    "OI Total ($)": None, "OI Chg 1H": None, "OI Chg 4H": None, "OI Chg 1D": None
                },
                use_container_width=True, hide_index=True
            )
            st.caption("🔴 RSI > 70 (Sobrecompra) | 🟢 RSI < 30 (Sobreventa)")
            
            st.divider()
            
            # --- SECCIÓN 3: FLUJO (VOLUMEN + OI) ---
            st.subheader("3. Flujo Institucional")
            st.dataframe(
                df,
                column_config={
                    "Activo": st.column_config.TextColumn("Crypto", width="small"),
                    
                    "Vol 1H": st.column_config.ProgressColumn("Vol 1H ($)", format="$%.0f", min_value=0, max_value=float(df['Vol 1H'].max() or 100)),
                    "Vol 4H": st.column_config.ProgressColumn("Vol 4H ($)", format="$%.0f", min_value=0, max_value=float(df['Vol 4H'].max() or 100)),
                    
                    "OI Total ($)": st.column_config.NumberColumn("Open Int. Total", format="$%.0f"),
                    "OI Chg 1H": st.column_config.NumberColumn("Δ OI 1H", format="%.2f%%"),
                    "OI Chg 4H": st.column_config.NumberColumn("Δ OI 4H", format="%.2f%%"),
                    "OI Chg 1D": st.column_config.NumberColumn("Δ OI 1D", format="%.2f%%"),
                    
                    "Precio ($)": None, "P.Chg 1H": None, "P.Chg 4H": None, "P.Chg 12H": None, "P.Chg 1D": None,
                    "RSI 15m": None, "RSI 1H": None, "RSI 4H": None, "RSI 12H": None, "RSI 1D": None, "RSI 1W": None,
                    "Vol 1D": None
                },
                use_container_width=True, hide_index=True
            )
            
            st.success("Análisis completado exitosamente.")

        else:
            st.warning("No llegaron datos válidos.")

except Exception as e:
    st.error(f"Error crítico: {e}")
