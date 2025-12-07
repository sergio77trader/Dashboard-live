import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - KuCoin Scanner")

# --- MAPEO DE TEMPORALIDADES ---
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w'
}

# --- LÓGICA HEIKIN ASHI ---
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

# --- CONEXIÓN AL MERCADO (KUCOIN) ---
@st.cache_data(ttl=3600)
def get_active_pairs():
    """Obtiene pares de Futuros de KuCoin (Suele permitir IP de EEUU)"""
    try:
        exchange = ccxt.kucoinfutures({'enableRateLimit': True})
        markets = exchange.load_markets()
        
        valid_pairs = []
        for symbol in markets:
            market = markets[symbol]
            # Filtramos solo contratos USDT
            if market['quote'] == 'USDT' and market['active']:
                valid_pairs.append(symbol)
                
        # KuCoin devuelve muchos pares, intentamos priorizar los clásicos si falla el ordenamiento
        # Para hacerlo rápido en nube, no pedimos volumen de todos (tarda mucho)
        # Priorizamos una lista manual de "Blue Chips" al principio si están disponibles
        priority = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT']
        
        # Ponemos los prioritarios primero, luego el resto
        sorted_pairs = [p for p in priority if p in valid_pairs] + [p for p in valid_pairs if p not in priority]
        
        return sorted_pairs

    except Exception as e:
        st.error(f"Error conectando a KuCoin: {e}")
        return []

def scan_market(targets):
    exchange = ccxt.kucoinfutures({'enableRateLimit': True})
    results = []
    
    prog = st.progress(0, text="Analizando Tendencias...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        # Actualizamos barra
        prog.progress((idx)/total, text=f"Procesando {symbol}...")
        
        row = {'Activo': symbol.replace(':USDT', '')} # Limpiamos nombre visualmente
        greens = 0
        valid = True
        
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                # Descarga de Velas
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=50)
                
                if not ohlcv:
                    row[tf_label] = "N/A"
                    valid = False
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                df_ha = calculate_heikin_ashi(df)
                last = df_ha.iloc[-1]
                
                # Diagnóstico de vela
                if last['HA_Close'] >= last['HA_Open']:
                    row[tf_label] = "🟢 ALCISTA"
                    greens += 1
                else:
                    row[tf_label] = "🔴 BAJISTA"
            except:
                row[tf_label] = "⚠️"
                valid = False
        
        if valid:
            if greens == 4: row['Diagnóstico'] = "🔥 FULL ALCISTA"
            elif greens == 0: row['Diagnóstico'] = "❄️ FULL BAJISTA"
            elif greens == 3: row['Diagnóstico'] = "✅ ALCISTA FUERTE"
            elif greens == 1: row['Diagnóstico'] = "🔻 BAJISTA FUERTE"
            else: row['Diagnóstico'] = "⚖️ MIXTO"
            
            results.append(row)
            
        # KuCoin es estricto con el Rate Limit, dormimos un poco
        time.sleep(0.15)
        
    prog.empty()
    return pd.DataFrame(results)

# --- FRONTEND ---
st.title("⚡ SystemaTrader: KuCoin Futures Scanner")
st.markdown("Monitor de Tendencia Fractal (Bypass Geo-Block)")

with st.sidebar:
    st.header("Configuración")
    
    if st.button("🔄 Recargar Pares"):
        st.cache_data.clear()
        
    with st.spinner("Conectando a KuCoin Futures..."):
        symbols = get_active_pairs()
        
    if symbols:
        st.success(f"En línea: {len(symbols)} contratos")
        
        # Selector de Cantidad
        limit = st.slider("Cantidad a Escanear:", 5, 50, 15)
        
        # Selector Manual
        manual = st.multiselect("Filtrar manual (Opcional):", symbols)
        
        go_btn = st.button("🚀 INICIAR ESCANEO", type="primary")
    else:
        st.error("No se pudo conectar a KuCoin. Revisa la conexión.")
        go_btn = False

if go_btn:
    # Definir objetivos
    targets = manual if manual else symbols[:limit]
    
    df = scan_market(targets)
    
    if not df.empty:
        # Ordenar
        sort_map = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
        df['sort'] = df['Diagnóstico'].map(sort_map).fillna(5)
        df = df.sort_values('sort').drop('sort', axis=1)
        
        # Filtros
        f_ver = st.radio("Ver:", ["Todo", "🔥 Full Bull", "❄️ Full Bear"], horizontal=True)
        
        if f_ver == "🔥 Full Bull":
            df = df[df['Diagnóstico'] == "🔥 FULL ALCISTA"]
        elif f_ver == "❄️ Full Bear":
            df = df[df['Diagnóstico'] == "❄️ FULL BAJISTA"]
            
        st.dataframe(
            df,
            column_config={
                "Activo": st.column_config.TextColumn("Contrato", width="medium"),
                "Diagnóstico": st.column_config.TextColumn("Estado Estructural", width="medium"),
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )
    else:
        st.warning("No se encontraron datos.")
