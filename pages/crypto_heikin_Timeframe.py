import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - PERPETUAL Scanner")

# --- MAPEO DE TEMPORALIDADES ---
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w'
}

# --- FUNCIONES DE CÁLCULO ---
def calculate_heikin_ashi(df):
    """Calcula HA con precisión matemática"""
    if df.empty: return df
    df_ha = df.copy()
    
    # HA Close
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    
    # HA Open (Requiere iteración para precisión)
    df_ha['HA_Open'] = 0.0
    df_ha.iat[0, df_ha.columns.get_loc('HA_Open')] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
    
    # Optimizamos el bucle usando numpy values para velocidad
    vals = df_ha.values
    idx_open = df_ha.columns.get_loc('HA_Open')
    idx_close = df_ha.columns.get_loc('HA_Close')
    
    for i in range(1, len(vals)):
        vals[i, idx_open] = (vals[i-1, idx_open] + vals[i-1, idx_close]) / 2
        
    df_ha['HA_Open'] = vals[:, idx_open]
    return df_ha

@st.cache_data(ttl=3600)
def get_all_perp_pairs():
    """
    Obtiene SOLO los contratos PERPETUOS (Swap) de Binance Futures USDT-M.
    Maneja errores de bloqueo de IP.
    """
    try:
        exchange = ccxt.binance({
            'options': {'defaultType': 'future'},
            'timeout': 10000,
            'enableRateLimit': True
        })
        
        # Carga de mercados (Aquí suele fallar si hay bloqueo)
        markets = exchange.load_markets()
        
        blacklist = ['USDC/USDT', 'BUSD/USDT', 'TUSD/USDT', 'USDP/USDT']
        valid_pairs = []
        
        for symbol in markets:
            market = markets[symbol]
            if market['quote'] == 'USDT' and market['type'] == 'swap' and market['active']:
                if symbol not in blacklist:
                    valid_pairs.append(symbol)
        
        # Ordenar por volumen (Requiere fetch_tickers)
        try:
            tickers = exchange.fetch_tickers(valid_pairs)
            valid_pairs.sort(key=lambda x: tickers[x]['quoteVolume'], reverse=True)
        except:
            pass 
        
        return valid_pairs

    except Exception as e:
        # Devolvemos lista vacía y el error no rompe la app
        return []

def get_market_scan(symbols_list, max_limit):
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    })
    
    results = []
    # Barra de progreso visual
    prog_bar = st.progress(0, text="Iniciando motor Heikin Ashi...")
    
    target_list = symbols_list[:max_limit]
    total = len(target_list)
    
    for idx, symbol in enumerate(target_list):
        # Actualizar texto de progreso
        prog_bar.progress((idx) / total, text=f"Analizando {symbol}...")
        
        row_data = {'Activo': symbol}
        greens = 0
        valid_candle = True
        
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=50)
                
                if not ohlcv:
                    row_data[tf_label] = "N/A"
                    valid_candle = False
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                df_ha = calculate_heikin_ashi(df)
                last = df_ha.iloc[-1]
                
                # Determinación de tendencia
                if last['HA_Close'] >= last['HA_Open']:
                    row_data[tf_label] = "🟢 ALCISTA"
                    greens += 1
                else:
                    row_data[tf_label] = "🔴 BAJISTA"
                    
            except Exception:
                row_data[tf_label] = "⚠️ Error"
                valid_candle = False
                # No dormimos aquí para ir más rápido, CCXT maneja el rate limit
        
        if valid_candle:
            # Diagnóstico
            if greens == 4: row_data['Diagnóstico'] = "🔥 FULL ALCISTA"
            elif greens == 0: row_data['Diagnóstico'] = "❄️ FULL BAJISTA"
            elif greens == 3: row_data['Diagnóstico'] = "✅ ALCISTA FUERTE"
            elif greens == 1: row_data['Diagnóstico'] = "🔻 BAJISTA FUERTE"
            else: row_data['Diagnóstico'] = "⚖️ MIXTO"
            
            results.append(row_data)
        
        # Pausa pequeña
        time.sleep(0.05) 
        
    prog_bar.empty()
    return pd.DataFrame(results)

# --- INTERFAZ ---
st.title("⚡ SystemaTrader: PERPETUALS Scanner")
st.markdown("Monitor de Tendencia Heikin Ashi (Binance Futures)")

# Sidebar
with st.sidebar:
    st.header("Configuración")
    
    if st.button("🔄 Recargar Mercados"):
        st.cache_data.clear()
        
    with st.spinner("Conectando con Binance Futures..."):
        all_symbols = get_all_perp_pairs()
    
    if all_symbols:
        st.success(f"Online: **{len(all_symbols)}** pares")
        
        # Slider dinámico (Evita error si la lista es corta)
        max_val = len(all_symbols)
        default_val = 20 if max_val >= 20 else max_val
        scan_limit = st.slider("Cantidad a Escanear:", 5, max_val, default_val)
        
        start_btn = st.button("🚀 INICIAR ESCANEO", type="primary")
    else:
        st.error("❌ Conexión Fallida")
        st.warning("""
        **Diagnóstico:** Binance ha bloqueado la IP de este servidor (EEUU).
        
        **Solución:** Debemos cambiar el script para usar **Bybit** o **KuCoin**.
        """)
        start_btn = False

# --- RESULTADOS ---
if start_btn:
    with st.spinner("Escaneando tendencias institucionales..."):
        df_results = get_market_scan(all_symbols, scan_limit)
        
        if not df_results.empty:
            # Ordenar
            sort_order = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
            df_results['sort_val'] = df_results['Diagnóstico'].map(sort_order).fillna(5)
            df_results = df_results.sort_values('sort_val').drop('sort_val', axis=1)
            
            # Filtros
            f_ver = st.radio("Filtro:", ["Ver Todo", "🔥 Solo Full Bull", "❄️ Solo Full Bear"], horizontal=True)
            
            if f_ver == "🔥 Solo Full Bull":
                df_show = df_results[df_results['Diagnóstico'] == "🔥 FULL ALCISTA"]
            elif f_ver == "❄️ Solo Full Bear":
                df_show = df_results[df_results['Diagnóstico'] == "❄️ FULL BAJISTA"]
            else:
                df_show = df_results
            
            st.dataframe(
                df_show,
                column_config={
                    "Activo": st.column_config.TextColumn("Contrato", width="medium"),
                    "Diagnóstico": st.column_config.TextColumn("Tendencia", width="medium"),
                },
                use_container_width=True,
                hide_index=True,
                height=600
            )
        else:
            st.error("No se obtuvieron datos válidos.")
else:
    if all_symbols:
        st.info("Sistema listo. Inicia el escaneo.")
