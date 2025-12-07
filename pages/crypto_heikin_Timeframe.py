import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - KuCoin Resilience")

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

# --- CÁLCULO HA SEGURO ---
def calculate_heikin_ashi(df):
    if df is None or df.empty or len(df) < 2: 
        return pd.DataFrame() # Retorno vacío seguro
    
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    df_ha['HA_Open'] = 0.0
    
    # Iniciar primera vela
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
            if markets[s]['quote'] == 'USDT' and markets[s]['active']:
                valid.append(s)
        
        # Prioridad manual (Blue Chips primero)
        majors = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT', 'BNB/USDT:USDT']
        sorted_pairs = [p for p in majors if p in valid] + [p for p in valid if p not in majors]
        return sorted_pairs
    except: return []

def scan_batch_safe(targets):
    # Instancia con timeout largo para evitar cortes
    exchange = ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })
    
    results = []
    prog = st.progress(0, text="Escaneando...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"Analizando: {symbol}")
        
        row = {'Activo': symbol.replace(':USDT', ''), 'Symbol_Raw': symbol}
        greens = 0
        valid_timeframes = 0
        
        # Iteramos cada temporalidad con protección individual
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                # Pedimos pocas velas (30) para ser rápidos
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=30)
                
                if not ohlcv or len(ohlcv) < 5: # Si hay menos de 5 velas, es muy nueva
                    row[tf_label] = "⚪" # Gris (Sin datos suficientes)
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
                row[tf_label] = "⚠️" # Error de conexión puntual
        
        # Lógica de Puntuación Adaptativa
        # Si la moneda es nueva y no tiene Mensual, no la penalizamos tanto
        if valid_timeframes > 0:
            ratio = greens / valid_timeframes
            
            if ratio == 1.0: row['Diagnóstico'] = "🔥 FULL ALCISTA" # Todo verde
            elif ratio == 0.0: row['Diagnóstico'] = "❄️ FULL BAJISTA" # Todo rojo
            elif ratio >= 0.75: row['Diagnóstico'] = "✅ ALCISTA FUERTE"
            elif ratio <= 0.25: row['Diagnóstico'] = "🔻 BAJISTA FUERTE"
            else: row['Diagnóstico'] = "⚖️ MIXTO"
            
            results.append(row)
        
        # Pausa de seguridad (Vital para que KuCoin no bloquee por pedir muchas velas)
        time.sleep(0.25)
        
    prog.empty()
    return pd.DataFrame(results)

# --- UI ---
st.title("⚡ SystemaTrader: KuCoin Safe Scanner")

with st.sidebar:
    if st.button("🔄 Recargar Mercado"):
        st.cache_data.clear()
        
    all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        st.divider()
        st.header("Escaneo por Lotes")
        
        # Lotes más pequeños por defecto para seguridad
        BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 50], index=1)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        
        batch_opts = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
        sel_batch = st.selectbox("Elegir:", range(len(batches)), format_func=lambda x: batch_opts[x])
        
        accumulate = st.checkbox("Acumular en tabla", value=True)
        
        if st.button("🚀 ESCANEAR", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Procesando... (Esto toma unos segundos por seguridad)"):
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
                        
                    st.success("Lote procesado exitosamente.")
                else:
                    st.warning("No se obtuvieron datos (Intenta un lote más pequeño).")
        
        if st.button("Limpiar"):
            st.session_state['crypto_results'] = []
            st.rerun()
    else:
        st.error("No conecta con KuCoin.")

# --- TABLA ---
if st.session_state['crypto_results']:
    df = pd.DataFrame(st.session_state['crypto_results'])
    
    # Ordenar
    sort_map = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
    df['sort'] = df['Diagnóstico'].map(sort_map).fillna(5)
    df = df.sort_values('sort').drop('sort', axis=1)
    
    # Filtro
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
    
    st.caption("Referencias: 🟢 Alcista | 🔴 Bajista | ⚪ Sin Datos (Moneda Nueva) | ⚠️ Error Conexión")
else:
    st.info("Selecciona un lote y escanea.")
