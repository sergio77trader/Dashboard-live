import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Stocks MACD Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS (TICKERS) ---
TICKERS = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX',
    'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'SAP', 'INTU', 'NOW',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX', 'HPQ', 'DELL',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS',
    'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'LUV', 'DAL',
    'F', 'GM', 'TM', 'HMC', 'STLA', 'RACE',
    'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO',
    'VZ', 'T', 'TMUS', 'VOD',
    'BABA', 'JD', 'BIDU', 'NIO', 'PDD', 'TCEHY', 'TCOM', 'BEKE', 'XPEV', 'LI', 'SONY',
    'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR',
    'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# --- MAPEO TEMPORAL YFINANCE ---
# (Label, Interval, Period)
TASKS = [
    ('15m', '15m', '5d'),   # 15 Minutos (Limitado a 5 días)
    ('1H',  '1h',  '1mo'),  # 1 Hora
    ('4H',  '1h',  '3mo'),  # 4 Horas (Resampleamos desde 1h para precisión)
    ('1D',  '1d',  '2y'),   # Diario
    ('1S',  '1wk', '5y'),   # Semanal
    ('1M',  '1mo', 'max')   # Mensual
]

# --- LÓGICA MACD ---
def get_macd_data(df, fast=12, slow=26, sig=9):
    """Retorna valor MACD Line y Estado"""
    if df.empty or len(df) < 35: return 0.0, "N/A"
    
    try:
        macd_df = df.ta.macd(fast=fast, slow=slow, signal=sig)
        if macd_df is None: return 0.0, "N/A"
        
        col_name = f'MACD_{fast}_{slow}_{sig}'
        macd_val = macd_df[col_name].iloc[-1]
        
        if pd.isna(macd_val): return 0.0, "N/A"
        
        state = "BULL" if macd_val > 0 else "BEAR"
        return float(macd_val), state
    except:
        return 0.0, "N/A"

# --- MOTOR DE ESCANEO ---
def scan_stocks(targets):
    results = []
    prog = st.progress(0, text="Escaneando mercado...")
    total = len(targets)
    
    for idx, ticker in enumerate(targets):
        prog.progress((idx)/total, text=f"Analizando {ticker}...")
        
        row = {'Activo': ticker}
        bull_count = 0
        valid_count = 0
        
        # Descarga inteligente: Bajamos datos base y resampleamos si es necesario
        # Para optimizar, hacemos requests separados por interval base
        
        for label, interval, period in TASKS:
            try:
                # Descarga
                df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
                
                # Limpieza MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                if df.empty:
                    row[label] = 0.0
                    continue
                
                # Caso especial 4H (Yahoo no da 4h nativo, resampleamos 1h)
                if label == '4H':
                    df_4h = df.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
                    val, state = get_macd_data(df_4h)
                else:
                    val, state = get_macd_data(df)
                
                row[label] = val
                
                if state == "BULL":
                    bull_count += 1
                    valid_count += 1
                elif state == "BEAR":
                    valid_count += 1
                    
            except:
                row[label] = 0.0
        
        # Diagnóstico Estructural
        if valid_count > 0:
            if bull_count == valid_count: row['Estructura'] = "🔥 FULL BULL"
            elif bull_count == 0: row['Estructura'] = "❄️ FULL BEAR"
            elif bull_count >= 4: row['Estructura'] = "✅ Mayoría Alcista"
            elif bull_count <= 2: row['Estructura'] = "🔻 Mayoría Bajista"
            else: row['Estructura'] = "⚖️ Mixto"
        else:
            row['Estructura'] = "-"

        results.append(row)
        # No necesitamos sleep en yfinance local/cloud de streamlit, es permisivo
        
    prog.empty()
    return pd.DataFrame(results)

# --- INTERFAZ ---
st.title("🎛️ SystemaTrader: Stocks MACD Matrix")
st.caption("Estructura de Tendencia (Línea MACD sobre/bajo 0)")

if 'stocks_macd' not in st.session_state:
    st.session_state['stocks_macd'] = []

with st.sidebar:
    st.header("Control")
    st.info(f"Total Activos: {len(TICKERS)}")
    
    # Selector de Lotes
    BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 50], index=1)
    batches = [TICKERS[i:i + BATCH_SIZE] for i in range(0, len(TICKERS), BATCH_SIZE)]
    batch_labels = [f"Lote {i+1} ({b[0]}...{b[-1]})" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        # Filtrar existentes
        existing = {x['Activo'] for x in st.session_state['stocks_macd']}
        to_run = [t for t in targets if t not in existing]
        
        if to_run:
            new_data = scan_stocks(to_run)
            st.session_state['stocks_macd'].extend(new_data.to_dict('records'))
            st.success("Datos agregados.")
        else:
            st.warning("Lote ya cargado.")

    if c2.button("🗑️ Limpiar"):
        st.session_state['stocks_macd'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['stocks_macd']:
    df = pd.DataFrame(st.session_state['stocks_macd'])
    
    # Ordenar
    sort_map = {"🔥 FULL BULL": 0, "❄️ FULL BEAR": 1, "✅ Mayoría Alcista": 2, "⚖️ Mixto": 3, "🔻 Mayoría Bajista": 4, "-": 5}
    df['sort'] = df['Estructura'].map(sort_map).fillna(6)
    df = df.sort_values('sort').drop('sort', axis=1)

    # Estilos
    def style_macd(val):
        if isinstance(val, (int, float)):
            if val > 0: return 'color: #00FF00; font-weight: bold; background-color: rgba(0,255,0,0.1)'
            if val < 0: return 'color: #FF4500; font-weight: bold; background-color: rgba(255,0,0,0.1)'
        return ''

    st.dataframe(
        df.style.applymap(style_macd, subset=['15m', '1H', '4H', '1D', '1S', '1M']),
        column_config={
            "Activo": st.column_config.TextColumn("Ticker", width="small", pinned=True),
            "15m": st.column_config.NumberColumn("15m", format="%.2f"),
            "1H": st.column_config.NumberColumn("1H", format="%.2f"),
            "4H": st.column_config.NumberColumn("4H", format="%.2f"),
            "1D": st.column_config.NumberColumn("Diario", format="%.2f"),
            "1S": st.column_config.NumberColumn("Semanal", format="%.2f"),
            "1M": st.column_config.NumberColumn("Mensual", format="%.2f"),
            "Estructura": st.column_config.TextColumn("Contexto", width="medium"),
        },
        use_container_width=True,
        hide_index=True,
        height=700
    )
else:
    st.info("👈 Selecciona un lote para escanear.")
