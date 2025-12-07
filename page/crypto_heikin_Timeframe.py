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
        # HA_Open = (Prev_Open + Prev_Close) / 2
        vals[i, idx_open] = (vals[i-1, idx_open] + vals[i-1, idx_close]) / 2
        
    df_ha['HA_Open'] = vals[:, idx_open]
    return df_ha

@st.cache_data(ttl=3600)
def get_all_perp_pairs():
    """
    Obtiene SOLO los contratos PERPETUOS (Swap) de Binance Futures USDT-M.
    """
    # INICIALIZACIÓN CLAVE: MODO FUTUROS
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'} 
    })
    
    try:
        markets = exchange.load_markets()
    except:
        return []

    # Lista negra de tokens inestables o ignorados
    blacklist = ['USDC/USDT', 'BUSD/USDT', 'TUSD/USDT']
    
    valid_pairs = []
    
    for symbol in markets:
        market = markets[symbol]
        # FILTRO ESTRICTO:
        # 1. Que sea contrato USDT
        # 2. Que sea SWAP (Perpetuo), no Future (Trimestral)
        # 3. Que esté activo
        if market['quote'] == 'USDT' and market['type'] == 'swap' and market['active']:
            if symbol not in blacklist:
                # Usamos el ID del ticker para obtener volumen si es necesario
                # Pero para velocidad, solo guardamos el símbolo por ahora
                valid_pairs.append(symbol)
    
    # Intentamos ordenar por volumen para mostrar los importantes primero
    # Esto requiere una llamada extra, pero vale la pena
    try:
        tickers = exchange.fetch_tickers(valid_pairs)
        # Ordenar lista de símbolos basada en el volumen del ticker
        valid_pairs.sort(key=lambda x: tickers[x]['quoteVolume'], reverse=True)
    except:
        pass # Si falla el ordenamiento, devolvemos la lista tal cual
    
    return valid_pairs

def get_market_scan(symbols_list, max_limit):
    # Instancia en modo FUTUROS
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'}
    })
    
    results = []
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    target_list = symbols_list[:max_limit]
    total = len(target_list)
    
    for idx, symbol in enumerate(target_list):
        status_text.text(f"Analizando Perpetuo {idx+1}/{total}: {symbol}...")
        
        row_data = {'Activo': symbol}
        greens = 0
        
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                # BAJAMOS 100 VELAS para asegurar la convergencia de Heikin Ashi
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
                
                if not ohlcv:
                    row_data[tf_label] = "N/A"
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
                time.sleep(0.1) # Pequeña pausa de seguridad
        
        # Diagnóstico SystemaTrader
        if greens == 4: row_data['Diagnóstico'] = "🔥 FULL ALCISTA"
        elif greens == 0: row_data['Diagnóstico'] = "❄️ FULL BAJISTA"
        elif greens == 3: row_data['Diagnóstico'] = "✅ ALCISTA FUERTE"
        elif greens == 1: row_data['Diagnóstico'] = "🔻 BAJISTA FUERTE"
        else: row_data['Diagnóstico'] = "⚖️ MIXTO"
        
        results.append(row_data)
        prog_bar.progress((idx + 1) / total)
        time.sleep(0.05) # Rate Limit Protection
        
    prog_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- INTERFAZ ---
st.title("⚡ SystemaTrader: PERPETUALS Scanner (Binance Futures)")
st.markdown("Monitor de Tendencia Heikin Ashi para el mercado de **Futuros Perpetuos**.")

# Sidebar
with st.sidebar:
    st.header("Configuración")
    
    if st.button("🔄 Refrescar Lista de Futuros"):
        st.cache_data.clear()
        
    with st.spinner("Conectando con Binance Futures..."):
        all_symbols = get_all_perp_pairs()
    
    st.success(f"Contratos Perpetuos Activos: **{len(all_symbols)}**")
    
    scan_limit = st.slider("Cantidad a Escanear (Top Volumen):", 10, len(all_symbols), 50)
    
    start_btn = st.button("🚀 INICIAR ESCANEO", type="primary")

# --- RESULTADOS ---
if start_btn:
    with st.spinner("Analizando mercado de derivados..."):
        df_results = get_market_scan(all_symbols, scan_limit)
        
        if not df_results.empty:
            # Ordenar por diagnóstico
            sort_order = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
            df_results['sort_val'] = df_results['Diagnóstico'].map(sort_order)
            df_results = df_results.sort_values('sort_val').drop('sort_val', axis=1)
            
            # Filtros
            f_ver = st.radio("Filtro Rápido:", ["Ver Todo", "🔥 Solo Full Bull", "❄️ Solo Full Bear"], horizontal=True)
            
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
                    "1H": st.column_config.TextColumn("1H", width="small"),
                    "4H": st.column_config.TextColumn("4H", width="small"),
                    "Diario": st.column_config.TextColumn("1D", width="small"),
                    "Semanal": st.column_config.TextColumn("1W", width="small"),
                    "Diagnóstico": st.column_config.TextColumn("Tendencia", width="medium"),
                },
                use_container_width=True,
                hide_index=True,
                height=600
            )
            
            # Link directo a Binance Futures
            st.markdown("---")
            if not df_show.empty:
                first_coin = df_show.iloc[0]['Activo'].replace('/', '')
                st.markdown(f"🔗 [Ir a Binance Futures ({first_coin})](https://www.binance.com/en/futures/{first_coin})")
                
        else:
            st.error("Error al conectar con Binance Futures.")
else:
    st.info("Configura y dale a Iniciar.")
