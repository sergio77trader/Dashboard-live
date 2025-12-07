import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - KuCoin Full Matrix")

# --- MEMORIA ---
if 'crypto_results' not in st.session_state:
    st.session_state['crypto_results'] = []

# --- MAPEO TEMPORAL ---
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w',
    'Mensual': '1M'
}

# --- CÁLCULO HEIKIN ASHI ---
def calculate_heikin_ashi(df):
    if df is None or df.empty or len(df) < 2: 
        return pd.DataFrame() 
    
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df_ha['HA_Open'] = 0.0
    
    # Inicializar la primera vela
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
    try:
        exchange = ccxt.kucoinfutures({'enableRateLimit': True})
        markets = exchange.load_markets()
        valid = []
        for s in markets:
            # Filtro: Contrato USDT y Activo
            if markets[s]['quote'] == 'USDT' and markets[s]['active']:
                valid.append(s)
        
        # Ordenamos: Majors primero, luego alfabético
        majors = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT', 'BNB/USDT:USDT', 'DOGE/USDT:USDT']
        sorted_pairs = [p for p in majors if p in valid] + sorted([p for p in valid if p not in majors])
        return sorted_pairs
    except: return []

def scan_batch_safe(targets):
    exchange = ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })
    
    results = []
    prog = st.progress(0, text="Escaneando...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"Procesando: {symbol}")
        
        row = {'Activo': symbol.replace(':USDT', ''), 'Symbol_Raw': symbol}
        greens = 0
        valid_timeframes = 0
        
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                # AJUSTE TÁCTICO:
                # Para mensual pedimos menos velas (12 = 1 año) para no estresar la API
                # Para el resto pedimos 30
                limit_req = 12 if tf_code == '1M' else 30
                
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit_req)
                
                # UMBRAL DE TOLERANCIA:
                # Antes pedíamos 5 velas. Ahora solo pedimos 2 (mínimo matemático para Heikin Ashi)
                if not ohlcv or len(ohlcv) < 2: 
                    row[tf_label] = "⚪" 
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                df_ha = calculate_heikin_ashi(df)
                
                if df_ha.empty:
                    row[tf_label] = "⚪"
                    continue

                last = df_ha.iloc[-1]
                
                if last['HA_Close'] >= last['HA_Open']:
                    row[tf_label] = "🟢"
                    greens += 1
                else:
                    row[tf_label] = "🔴"
                
                valid_timeframes += 1
                
            except Exception:
                row[tf_label] = "⚠️"
        
        # Puntuación Elástica
        # Si un timeframe falló (ej: mensual vacío), calculamos el % sobre los que sí funcionaron
        if valid_timeframes > 0:
            ratio = greens / valid_timeframes
            
            # Ajuste visual del diagnóstico
            if ratio == 1.0: row['Diagnóstico'] = "🔥 FULL ALCISTA"
            elif ratio == 0.0: row['Diagnóstico'] = "❄️ FULL BAJISTA"
            elif ratio >= 0.75: row['Diagnóstico'] = "✅ ALCISTA FUERTE"
            elif ratio <= 0.25: row['Diagnóstico'] = "🔻 BAJISTA FUERTE"
            else: row['Diagnóstico'] = "⚖️ MIXTO"
            
            results.append(row)
        
        time.sleep(0.25) # Respetar límites API
        
    prog.empty()
    return pd.DataFrame(results)

# --- UI ---
st.title("⚡ SystemaTrader: KuCoin Futures Matrix")

with st.sidebar:
    if st.button("🔄 Recargar Mercado"):
        st.cache_data.clear()
        
    all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        st.divider()
        st.header("Escaneo por Lotes")
        
        BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 50], index=1)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        
        batch_opts = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
        sel_batch = st.selectbox("Elegir:", range(len(batches)), format_func=lambda x: batch_opts[x])
        
        accumulate = st.checkbox("Acumular en tabla", value=True)
        
        if st.button("🚀 ESCANEAR", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Procesando..."):
                new_df = scan_batch_safe(target)
                
                if not new_df.empty:
                    new_data = new_df.to_dict('records')
                    if accumulate:
                        existing = {x['Activo'] for x in st.session_state['crypto_results']}
                        for item in new_data:
                            if item['Activo'] not in existing:
                                st.session_state['crypto_results'].append(item)
                    else:
                        st.session_state['crypto_results'] = new_data
                    st.success("Lote procesado.")
                else:
                    st.warning("Sin datos válidos en este lote.")
        
        if st.button("Limpiar"):
            st.session_state['crypto_results'] = []
            st.rerun()
    else:
        st.error("No conecta con KuCoin.")

# --- TABLA ---
if st.session_state['crypto_results']:
    df = pd.DataFrame(st.session_state['crypto_results'])
    
    # Mapeo numérico para ordenar
    sort_map = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
    df['sort'] = df['Diagnóstico'].map(sort_map).fillna(5)
    df = df.sort_values('sort').drop('sort', axis=1)
    
    f_mode = st.radio("Filtro:", ["Todos", "🔥 Oportunidades"], horizontal=True)
    if f_mode == "🔥 Oportunidades":
        df = df[df['Diagnóstico'].isin(["🔥 FULL ALCISTA", "❄️ FULL BAJISTA"])]

    st.dataframe(
        df,
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small"),
            "1H": st.column_config.TextColumn("1H", width="small"),
            "4H": st.column_config.TextColumn("4H", width="small"),
            "Diario": st.column_config.TextColumn("D", width="small"),
            "Semanal": st.column_config.TextColumn("S", width="small"),
            "Mensual": st.column_config.TextColumn("M", width="small"),
            "Diagnóstico": st.column_config.TextColumn("Estado", width="medium"),
            "Symbol_Raw": None
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )
else:
    st.info("Selecciona un lote y escanea.")
