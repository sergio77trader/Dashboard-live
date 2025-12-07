import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - KuCoin Full Scanner")

# --- GESTIÓN DE ESTADO (MEMORIA) ---
if 'crypto_results' not in st.session_state:
    st.session_state['crypto_results'] = []

# --- MAPEO DE TEMPORALIDADES (AHORA CON MENSUAL) ---
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w',
    'Mensual': '1M' # Nueva temporalidad Macro
}

# --- FUNCIONES TÉCNICAS ---
def calculate_heikin_ashi(df):
    if df.empty: return df
    df_ha = df.copy()
    
    # HA Close
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    
    # HA Open
    df_ha['HA_Open'] = 0.0
    df_ha.iat[0, df_ha.columns.get_loc('HA_Open')] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
    
    vals = df_ha.values
    idx_open = df_ha.columns.get_loc('HA_Open')
    idx_close = df_ha.columns.get_loc('HA_Close')
    
    for i in range(1, len(vals)):
        vals[i, idx_open] = (vals[i-1, idx_open] + vals[i-1, idx_close]) / 2
        
    df_ha['HA_Open'] = vals[:, idx_open]
    return df_ha

@st.cache_data(ttl=3600)
def get_active_pairs():
    """Obtiene todos los pares de Futuros de KuCoin"""
    try:
        exchange = ccxt.kucoinfutures({'enableRateLimit': True})
        markets = exchange.load_markets()
        
        valid_pairs = []
        for symbol in markets:
            market = markets[symbol]
            if market['quote'] == 'USDT' and market['active']:
                valid_pairs.append(symbol)
                
        # Prioridad manual para que los importantes salgan en los primeros lotes
        majors = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT']
        sorted_pairs = [p for p in majors if p in valid_pairs] + [p for p in valid_pairs if p not in majors]
        
        return sorted_pairs

    except Exception as e:
        return []

def scan_market_batch(targets):
    exchange = ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000 
    })
    results = []
    
    prog = st.progress(0, text="Analizando fractales...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"Procesando: {symbol}")
        
        # Limpieza de nombre
        display_name = symbol.replace(':USDT', '')
        row = {'Activo': display_name, 'Symbol_Raw': symbol}
        
        greens = 0
        valid = True
        
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                # Descarga de velas
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=30) # 30 velas sobran para HA actual
                
                if not ohlcv:
                    row[tf_label] = "N/A"
                    valid = False
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                df_ha = calculate_heikin_ashi(df)
                last = df_ha.iloc[-1]
                
                # Diagnóstico
                if last['HA_Close'] >= last['HA_Open']:
                    row[tf_label] = "🟢" # Solo icono para ahorrar espacio
                    greens += 1
                else:
                    row[tf_label] = "🔴"
            except:
                row[tf_label] = "⚠️"
                valid = False
        
        if valid:
            # Nuevo Sistema de Puntuación (Max 5 puntos)
            if greens == 5: row['Diagnóstico'] = "🔥 FULL ALCISTA"
            elif greens == 0: row['Diagnóstico'] = "❄️ FULL BAJISTA"
            elif greens >= 4: row['Diagnóstico'] = "✅ ALCISTA FUERTE"
            elif greens <= 1: row['Diagnóstico'] = "🔻 BAJISTA FUERTE"
            else: row['Diagnóstico'] = "⚖️ MIXTO"
            
            results.append(row)
            
        # Rate Limit Sleep (Vital para KuCoin en bucles)
        time.sleep(0.2)
        
    prog.empty()
    return pd.DataFrame(results)

# --- FRONTEND ---
st.title("⚡ SystemaTrader: KuCoin Futures Matrix (1H a 1M)")
st.caption("Monitor de Tendencia Fractal Acumulativo")

with st.sidebar:
    st.header("Configuración")
    
    if st.button("🔄 Recargar Lista Total"):
        st.cache_data.clear()
        
    with st.spinner("Conectando a KuCoin Futures..."):
        all_symbols = get_active_pairs()
        
    if all_symbols:
        st.success(f"Total Mercado: **{len(all_symbols)}** contratos")
        
        st.divider()
        st.header("🔬 Escaneo por Lotes")
        
        # 1. Definir Lotes
        BATCH_SIZE = st.selectbox("Tamaño del Lote:", [20, 50, 100], index=0)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        
        # 2. Selector
        batch_labels = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
        sel_batch_idx = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
        
        # 3. Acción
        if st.button("🚀 ESCANEAR Y ACUMULAR", type="primary"):
            targets = batches[sel_batch_idx]
            with st.spinner(f"Analizando {len(targets)} criptomonedas..."):
                new_data_df = scan_market_batch(targets)
                
                if not new_data_df.empty:
                    # Convertir a lista de dicts para acumular
                    new_data = new_data_df.to_dict('records')
                    
                    # Evitar duplicados
                    current_symbols = {item['Activo'] for item in st.session_state['crypto_results']}
                    added = 0
                    for item in new_data:
                        if item['Activo'] not in current_symbols:
                            st.session_state['crypto_results'].append(item)
                            added += 1
                    st.success(f"Procesado. +{added} nuevos activos.")
                else:
                    st.warning("El lote no devolvió datos válidos.")

        # 4. Gestión
        st.markdown("---")
        total_scanned = len(st.session_state['crypto_results'])
        st.metric("Total en Tabla", f"{total_scanned} / {len(all_symbols)}")
        st.progress(total_scanned / len(all_symbols))
        
        if st.button("🗑️ Limpiar Tabla"):
            st.session_state['crypto_results'] = []
            st.rerun()
            
    else:
        st.error("Error de conexión con KuCoin.")

# --- RESULTADOS ---
if st.session_state['crypto_results']:
    df = pd.DataFrame(st.session_state['crypto_results'])
    
    # Ordenar por diagnóstico
    sort_map = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
    df['sort'] = df['Diagnóstico'].map(sort_map).fillna(5)
    df = df.sort_values('sort').drop('sort', axis=1)
    
    # Filtros
    col1, col2 = st.columns([2, 1])
    with col1:
        f_ver = st.radio("Filtro Visual:", ["Todo", "🔥 Oportunidades (Full Bull/Bear)"], horizontal=True)
    
    if f_ver == "🔥 Oportunidades (Full Bull/Bear)":
        df = df[df['Diagnóstico'].isin(["🔥 FULL ALCISTA", "❄️ FULL BAJISTA"])]
        
    st.subheader("Radar de Tendencias")
    st.dataframe(
        df,
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small"),
            "1H": st.column_config.TextColumn("1H", width="small"),
            "4H": st.column_config.TextColumn("4H", width="small"),
            "Diario": st.column_config.TextColumn("1D", width="small"),
            "Semanal": st.column_config.TextColumn("1W", width="small"),
            "Mensual": st.column_config.TextColumn("1M", width="small"), # Nueva columna visual
            "Diagnóstico": st.column_config.TextColumn("Estructura", width="medium"),
            "Symbol_Raw": None # Ocultar columna técnica
        },
        use_container_width=True,
        hide_index=True,
        height=700
    )
else:
    st.info("👈 Selecciona un lote en la izquierda y presiona 'Escanear y Acumular'.")
