import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Tablero Maestro v2")

# --- BASE DE DATOS ---
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

# --- 1. MATEMÁTICA EXACTA ---
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
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1) # 1 Verde, -1 Rojo
    
    return df

# --- 2. MOTOR DE SIMULACIÓN ---
def run_simulation_for_ticker(ticker, interval, period):
    try:
        # Corrección de yfinance: multi_level_index=False evita problemas de formato
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        
        if df.empty: return "N/A", "Sin Datos", 0
        
        # Limpieza extra por si acaso
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        
        position = "FLAT" 
        entry_price = 0.0
        entry_date = None
        
        # Bucle Vela por Vela
        for i in range(1, len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            c_ha = df['HA_Color'].iloc[i]
            c_hist = df['Hist'].iloc[i]
            p_hist = df['Hist'].iloc[i-1]
            
            # --- SALIDAS ---
            if position == "LONG" and c_hist < p_hist:
                position = "FLAT"
            elif position == "SHORT" and c_hist > p_hist:
                position = "FLAT"

            # --- ENTRADAS ---
            if position == "FLAT":
                # LONG: HA cambia a Verde + Hist < 0 + Hist Subiendo
                if c_ha == 1 and (c_hist < 0) and (c_hist > p_hist):
                    position = "LONG"
                    entry_date = date
                    entry_price = price
                    
                # SHORT: HA cambia a Rojo + Hist > 0 + Hist Bajando
                elif c_ha == -1 and (c_hist > 0) and (c_hist < p_hist):
                    position = "SHORT"
                    entry_date = date
                    entry_price = price
        
        # Formatear Salida
        current_price = df['Close'].iloc[-1]
        
        # --- INFO PARA NEUTRO ---
        if position == "FLAT":
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Estado HA
            ha_status = "🟢" if last_row['HA_Color'] == 1 else "🔴"
            
            # Estado MACD (Momentum)
            macd_status = "🟢" if last_row['Hist'] > prev_row['Hist'] else "🔴"
            
            info_neutro = f"HA {ha_status} | MACD {macd_status}"
            return "⚪ NEUTRO", info_neutro, current_price
        
        # Calcular PnL Latente
        if position == "LONG":
            pnl = ((current_price - entry_price) / entry_price) * 100
            tipo = "🟢 LONG"
        else:
            pnl = ((entry_price - current_price) / entry_price) * 100
            tipo = "🔴 SHORT"
            
        f_date = entry_date.strftime('%d/%m/%y')
        info = f"Desde: {f_date} (${entry_price:.2f}) | PnL: {pnl:+.1f}%"
        
        return tipo, info, current_price

    except Exception:
        return "ERROR", "Fallo cálculo", 0

# --- 3. PROCESAMIENTO POR LOTE ---
def process_batch(tickers):
    results = []
    prog = st.progress(0)
    
    configs = [
        ("M", "1mo", "max"), 
        ("S", "1wk", "10y"), 
        ("D", "1d", "5y")
    ]
    
    total = len(tickers)
    for i, t in enumerate(tickers):
        row = {"Ticker": t, "Precio": 0}
        
        for col_prefix, interval, period in configs:
            try:
                sig, info, price = run_simulation_for_ticker(t, interval, period)
                row[f"{col_prefix}_Signal"] = sig
                row[f"{col_prefix}_Info"] = info
                if price > 0: row["Precio"] = price
            except:
                row[f"{col_prefix}_Signal"] = "Error"
                row[f"{col_prefix}_Info"] = "-"
        
        results.append(row)
        prog.progress((i + 1) / total)
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("📊 Tablero Maestro: HA + MACD")

if 'master_results' not in st.session_state:
    st.session_state['master_results'] = []

with st.sidebar:
    st.header("Control de Lotes")
    st.info(f"Total Activos: {len(TICKERS)}")
    
    batch_size = st.slider("Tamaño del Lote", 5, 50, 10)
    batches = [TICKERS[i:i + batch_size] for i in range(0, len(TICKERS), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        # Filtrar ya existentes
        existing = [x['Ticker'] for x in st.session_state['master_results']]
        to_run = [t for t in targets if t not in existing]
        
        if to_run:
            new_data = process_batch(to_run)
            st.session_state['master_results'].extend(new_data)
        else:
            st.warning("Lote ya escaneado.")

    if c2.button("🗑️ Limpiar"):
        st.session_state['master_results'] = []
        st.rerun()

# --- MOSTRAR TABLA ---
if st.session_state['master_results']:
    df = pd.DataFrame(st.session_state['master_results'])
    
    def style_signal(val):
        if "LONG" in str(val): return "color: #00ff00; font-weight: bold; background-color: rgba(0,255,0,0.1)"
        if "SHORT" in str(val): return "color: #ff3333; font-weight: bold; background-color: rgba(255,0,0,0.1)"
        return "color: #888"

    # Usamos applymap (compatible con versiones anteriores de pandas en algunos envs de streamlit)
    st.dataframe(
        df.style.applymap(style_signal, subset=['M_Signal', 'S_Signal', 'D_Signal']),
        column_config={
            "Ticker": st.column_config.TextColumn("Activo", width="small", pinned=True),
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            
            "M_Signal": st.column_config.TextColumn("Mensual"),
            "M_Info": st.column_config.TextColumn("Detalle Mensual", width="medium"),
            
            "S_Signal": st.column_config.TextColumn("Semanal"),
            "S_Info": st.column_config.TextColumn("Detalle Semanal", width="medium"),
            
            "D_Signal": st.column_config.TextColumn("Diario"),
            "D_Info": st.column_config.TextColumn("Detalle Diario", width="medium"),
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    st.divider()
    st.info("""
    **Leyenda para NEUTRO:**
    *   **HA 🟢:** Vela Heikin Ashi Verde (Tendencia alcista).
    *   **MACD 🟢:** Histograma subiendo (Momentum ganando fuerza al alza).
    *   *Si ves HA 🟢 | MACD 🟢 en NEUTRO, podría estar cerca de dar entrada LONG.*
    """)

else:
    st.info("👈 Selecciona un lote para comenzar.")
