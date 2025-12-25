import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Cripto Master HA+MACD")

# --- ESTILOS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 16px; }
    .stProgress > div > div > div > div { background-color: #00CC96; }
</style>
""", unsafe_allow_html=True)

# --- 1. MOTOR DE DATOS (KUCOIN) ---
@st.cache_data(ttl=3600)
def get_kucoin_symbols():
    """Obtiene todos los pares USDT de KuCoin Futures ordenados por volumen"""
    try:
        exchange = ccxt.kucoinfutures()
        tickers = exchange.fetch_tickers()
        valid = []
        
        for s in tickers:
            # Filtro: Pares USDT con volumen
            if '/USDT:USDT' in s and tickers[s].get('quoteVolume'):
                valid.append({
                    'symbol': s, 
                    'vol': tickers[s]['quoteVolume']
                })
        
        # Ordenar por volumen descendente
        df = pd.DataFrame(valid).sort_values('vol', ascending=False)
        return df['symbol'].tolist()
    except:
        # Fallback de emergencia
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT']

def get_crypto_data(symbol, timeframe, limit=200):
    exchange = ccxt.kucoinfutures({'enableRateLimit': True})
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv: return pd.DataFrame()
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except:
        return pd.DataFrame()

# --- 2. MATEMÁTICA EXACTA (TU ESTRATEGIA) ---
def calculate_indicators(df, fast=12, slow=26, sig=9):
    # MACD
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    df['Hist'] = hist
    
    # Heikin Ashi Iterativo
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        prev_o = ha_open[-1]
        prev_c = ha_close.iloc[i-1]
        ha_open.append((prev_o + prev_c) / 2)
        
    df['HA_Close'] = ha_close
    df['HA_Open'] = ha_open
    # 1 Verde, -1 Rojo
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1)
    
    return df

# --- 3. MOTOR DE SIMULACIÓN ---
def run_simulation(df):
    if df.empty: return "N/A", "-", 0
    
    df = calculate_indicators(df)
    
    position = "FLAT"
    entry_price = 0.0
    entry_date = None
    
    # Recorremos la historia para encontrar el estado actual
    for i in range(1, len(df)):
        date = df['Date'].iloc[i]
        price = df['Close'].iloc[i]
        
        c_ha = df['HA_Color'].iloc[i]
        c_hist = df['Hist'].iloc[i]
        p_hist = df['Hist'].iloc[i-1]
        
        # SALIDAS (Cruce de histograma en contra)
        if position == "LONG" and c_hist < p_hist: position = "FLAT"
        if position == "SHORT" and c_hist > p_hist: position = "FLAT"
        
        # ENTRADAS
        if position == "FLAT":
            # LONG: HA Verde + Hist < 0 (Valle) + Hist Subiendo
            if c_ha == 1 and (c_hist < 0) and (c_hist > p_hist):
                position = "LONG"
                entry_date = date
                entry_price = price
            # SHORT: HA Rojo + Hist > 0 (Pico) + Hist Bajando
            elif c_ha == -1 and (c_hist > 0) and (c_hist < p_hist):
                position = "SHORT"
                entry_date = date
                entry_price = price
    
    current_price = df['Close'].iloc[-1]
    
    # --- RESULTADO NEUTRO ---
    if position == "FLAT":
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        ha_st = "🟢" if last['HA_Color'] == 1 else "🔴"
        macd_st = "🟢" if last['Hist'] > prev['Hist'] else "🔴"
        
        info = f"HA {ha_st} | MACD {macd_st}"
        return "⚪ NEUTRO", info, current_price
    
    # --- RESULTADO ACTIVO ---
    if position == "LONG":
        pnl = ((current_price - entry_price) / entry_price) * 100
        tipo = "🟢 LONG"
    else:
        pnl = ((entry_price - current_price) / entry_price) * 100
        tipo = "🔴 SHORT"
        
    # Formato de fecha corto para Cripto
    f_date = entry_date.strftime('%d/%m %H:%M') if entry_date else "-"
    info = f"Entrada: ${entry_price:.4f} ({f_date}) | PnL: {pnl:+.2f}%"
    
    return tipo, info, current_price

# --- 4. PROCESAMIENTO POR LOTE ---
def process_batch_crypto(tickers):
    results = []
    prog = st.progress(0, text="Analizando fractales...")
    
    # Configuración de Timeframes Cripto (CCXT codes)
    # Usamos 1 Semana, 1 Día, 4 Horas (La triada estándar cripto)
    configs = [
        ("S", "1w"), # Semanal
        ("D", "1d"), # Diario
        ("4H", "4h") # 4 Horas
    ]
    
    total = len(tickers)
    
    for i, symbol in enumerate(tickers):
        clean_name = symbol.replace(':USDT', '').replace('/USDT', '')
        prog.progress((i)/total, text=f"Procesando {clean_name}...")
        
        row = {"Activo": clean_name, "Precio": 0}
        
        for col_prefix, tf_code in configs:
            try:
                # Descargamos datos
                df = get_crypto_data(symbol, tf_code)
                sig, info, price = run_simulation(df)
                
                row[f"{col_prefix}_Signal"] = sig
                row[f"{col_prefix}_Info"] = info
                
                # Guardamos precio (preferentemente del 4H que es el ultimo loop)
                if price > 0: row["Precio"] = price
                
            except:
                row[f"{col_prefix}_Signal"] = "Error"
                row[f"{col_prefix}_Info"] = "-"
        
        results.append(row)
        time.sleep(0.15) # Rate limit suave
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🛡️ Cripto Master: HA + MACD Strategy")
st.caption("Estrategia de Reversión de Momentum sobre Tendencia Heikin Ashi")

# Estado de memoria
if 'crypto_master_results' not in st.session_state:
    st.session_state['crypto_master_results'] = []

with st.sidebar:
    st.header("Control de Misión")
    
    with st.spinner("Cargando mercado..."):
        all_symbols = get_kucoin_symbols()
    
    st.success(f"Mercado Total: {len(all_symbols)} pares")
    
    # Configuración de Lotes
    BATCH_SIZE = st.selectbox("Tamaño del Lote:", [10, 20, 50], index=1)
    batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    
    batch_opts = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_opts[x])
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        # Filtrar los que ya tenemos para no repetir
        existing = {x['Activo'] for x in st.session_state['crypto_master_results']}
        
        # Ajustamos lógica de filtrado para coincidir nombres
        to_run = [t for t in targets if t.replace(':USDT', '').replace('/USDT', '') not in existing]
        
        if to_run:
            new_data = process_batch_crypto(to_run)
            st.session_state['crypto_master_results'].extend(new_data)
            st.success(f"Procesados {len(new_data)} nuevos activos.")
        else:
            st.warning("Este lote ya está en la tabla.")

    if c2.button("🗑️ Limpiar"):
        st.session_state['crypto_master_results'] = []
        st.rerun()

# --- TABLA DE RESULTADOS ---
if st.session_state['crypto_master_results']:
    df = pd.DataFrame(st.session_state['crypto_master_results'])
    
    # Función de estilos (Verde Long, Rojo Short)
    def style_signal(val):
        if "LONG" in str(val): return "color: #00ff00; font-weight: bold; background-color: rgba(0,255,0,0.1)"
        if "SHORT" in str(val): return "color: #ff3333; font-weight: bold; background-color: rgba(255,0,0,0.1)"
        return "color: #888"

    st.dataframe(
        df.style.applymap(style_signal, subset=['S_Signal', 'D_Signal', '4H_Signal']),
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small", pinned=True),
            "Precio": st.column_config.NumberColumn(format="$%.4f"),
            
            "S_Signal": st.column_config.TextColumn("Semanal"),
            "S_Info": st.column_config.TextColumn("Detalle Semanal", width="medium"),
            
            "D_Signal": st.column_config.TextColumn("Diario"),
            "D_Info": st.column_config.TextColumn("Detalle Diario", width="medium"),
            
            "4H_Signal": st.column_config.TextColumn("4 Horas"),
            "4H_Info": st.column_config.TextColumn("Detalle 4H", width="medium"),
        },
        use_container_width=True,
        hide_index=True,
        height=700
    )
    
    st.markdown("---")
    st.info("""
    **Estrategia "SystemaTrader Reversal":**
    *   **ENTRADA LONG:** Vela Heikin Ashi cambia a Verde + Histograma MACD es negativo (bajo cero) pero empieza a subir.
    *   **ENTRADA SHORT:** Vela Heikin Ashi cambia a Roja + Histograma MACD es positivo (sobre cero) pero empieza a bajar.
    *   **SALIDA:** Cuando el Histograma pierde fuerza (se da la vuelta) en contra de la posición.
    """)

else:
    st.info("👈 Selecciona un lote en el menú lateral para comenzar el análisis.")
