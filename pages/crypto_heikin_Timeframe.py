import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Bybit Scanner")

# --- MAPEO DE TEMPORALIDADES ---
TIMEFRAMES = {
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w'
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
def get_bybit_pairs():
    """Obtiene pares USDT Perpetuos de Bybit (Linear)"""
    try:
        # Inicializamos Bybit
        exchange = ccxt.bybit({'enableRateLimit': True})
        markets = exchange.load_markets()
        
        valid_pairs = []
        
        for symbol in markets:
            market = markets[symbol]
            # Filtro para Perpetuos USDT (Linear)
            # En Bybit, 'linear' suele referirse a los contratos USDT
            if market.get('linear', False) and market['quote'] == 'USDT' and market['active']:
                valid_pairs.append(symbol)
                
        # Intentamos ordenar por volumen
        try:
            # Pedimos tickers solo de los válidos para no saturar
            # Si son muchos (>100), Bybit puede quejarse, así que pedimos todos los tickers de una vez
            all_tickers = exchange.fetch_tickers()
            
            # Filtramos solo los que nos interesan y ordenamos
            pairs_with_vol = []
            for s in valid_pairs:
                if s in all_tickers:
                    vol = all_tickers[s]['quoteVolume'] if all_tickers[s]['quoteVolume'] else 0
                    pairs_with_vol.append((s, vol))
            
            # Orden descendente por volumen
            pairs_with_vol.sort(key=lambda x: x[1], reverse=True)
            return [x[0] for x in pairs_with_vol]
            
        except:
            return valid_pairs

    except Exception as e:
        st.error(f"Error Bybit: {e}")
        return []

def scan_market(targets):
    exchange = ccxt.bybit({'enableRateLimit': True})
    results = []
    
    prog = st.progress(0, text="Escaneando Bybit...")
    total = len(targets)
    
    for idx, symbol in enumerate(targets):
        prog.progress((idx)/total, text=f"Analizando {symbol}...")
        
        row = {'Activo': symbol}
        greens = 0
        valid = True
        
        for tf_label, tf_code in TIMEFRAMES.items():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=50)
                if not ohlcv:
                    row[tf_label] = "N/A"
                    valid = False
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                df_ha = calculate_heikin_ashi(df)
                last = df_ha.iloc[-1]
                
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
            
        time.sleep(0.1) # Respetar límites API
        
    prog.empty()
    return pd.DataFrame(results)

# --- INTERFAZ ---
st.title("🦅 SystemaTrader: Bybit Futures Scanner")
st.caption("Conexión directa a derivados cripto (Bypass Geo-Block)")

with st.sidebar:
    st.header("Configuración")
    
    if st.button("🔄 Recargar Mercados"):
        st.cache_data.clear()
    
    with st.spinner("Conectando a Bybit..."):
        symbols = get_bybit_pairs()
        
    if symbols:
        st.success(f"Conectado: {len(symbols)} contratos")
        limit = st.slider("Escanear Top:", 5, 50, 15)
        go_btn = st.button("🚀 INICIAR ESCANEO", type="primary")
    else:
        st.error("No se pudo conectar a Bybit.")
        go_btn = False

if go_btn:
    # Limpiar nombre del simbolo para que se vea bonito (BTC/USDT:USDT -> BTC/USDT)
    clean_targets = symbols[:limit]
    
    df = scan_market(clean_targets)
    
    if not df.empty:
        # Limpieza visual de nombres
        df['Activo'] = df['Activo'].apply(lambda x: x.split(':')[0])
        
        # Ordenar
        sort_map = {"🔥 FULL ALCISTA": 0, "❄️ FULL BAJISTA": 1, "✅ ALCISTA FUERTE": 2, "🔻 BAJISTA FUERTE": 3, "⚖️ MIXTO": 4}
        df['sort'] = df['Diagnóstico'].map(sort_map)
        df = df.sort_values('sort').drop('sort', axis=1)
        
        st.dataframe(
            df,
            column_config={
                "Activo": st.column_config.TextColumn("Ticker", width="medium"),
                "Diagnóstico": st.column_config.TextColumn("Tendencia Global", width="medium"),
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )
    else:
        st.warning("No hay datos.")
