import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader 360: Diamond")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div[data-testid="stMetric"], .metric-cardIN'],
    '💊 Salud': ['LLY', 'NVO', 'JNJ', 'PFE', 'MRK', 'ABBV', 'UNH', 'BMY', 'AMGN'],
    '🛒 Consumo': ['KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'PG'],
    '🏭 Industria': ['XOM', 'CVX', 'SLB', 'BA', 'CAT', 'DE', 'GE', '

Copia, pega y ejecuta.

```python
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime

# {
        background-color: transparent !important;
        border: 1px solid #e0e0e0;
        padding: 15px; border-radius: 8px; text-align: center;
        min-height: 160px; display: flex; flex-direction: column;MMM', 'LMT', 'F', 'GM'],
    '🇧🇷 Brasil': ['PBR', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV'],
    '🇨🇳 China': ['BABA', 'JD', 'BIDU', 'PDD', 'NIO'],
    ' --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Systema justify-content: center;
    }
    @media (prefers-color-scheme: dark) {⛏️ Minería': ['GOLD', 'NEM', 'FCX', 'SCCO'],
    '📈Trader 360: Platinum V2")

# --- ESTILOS CSS ---
st.markdown("""
 ETFs': ['SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ
        div[data-testid="stMetric"], .metric-card { border: 1px solid #4<style>
    div[data-testid="stMetric"], .metric-card {
        background-color', 'XLE', 'XLF', 'XLK', 'XLV', 'ARKK', 'GLD04040; }
    }
    .big-score { font-size: 2.: transparent !important;
        border: 1px solid #e0e0e0;
        padding', 'SLV', 'GDX', 'XLY', 'XLP']
}
CEDEAR_DATABASE2rem; font-weight: 800; margin: 5px 0; }
    . = sorted(list(set([item for sublist in DB_CATEGORIES.values() for item in sublist: 15px; border-radius: 8px; text-align: center;
        min-score-label { font-size: 0.8rem; font-weight: 600; textheight: 160px; display: flex; flex-direction: column; justify-content: center;])))

# --- INICIALIZAR ESTADO (V11) ---
if 'st360_-transform: uppercase; opacity: 0.8; }
    .sub-info { font-size:db_v11' not in st.session_state: st.session_state['st360
    }
    @media (prefers-color-scheme: dark) {
        div[data- 0.8rem; color: #666; }
    
    .context-box { paddingtestid="stMetric"], .metric-card { border: 1px solid #404040;_db_v11'] = []

# --- HELPERS MATEMÁTICOS ---
def calculate_: 10px; border-radius: 5px; margin-bottom: 15px; border }
    }
    .big-score { font-size: 2.2rem; font-weightrsi(series, period=14):
    delta = series.diff()
    gain = (delta.-left: 4px solid #ccc; font-size: 0.9rem;}
    
    where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta: 800; margin: 5px 0; }
    .score-label { font-.alert-tag {
        font-size: 0.75rem; font-weight: bold;size: 0.8rem; font-weight: 600; text-transform: uppercase; opacity.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain padding: 3px 8px; border-radius: 4px; margin-top: 6px; / loss
    return 100 - (100 / (1 + rs))

def calculate_: 0.8; }
    .sub-info { font-size: 0.8rem; display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---atr(df, period=14):
    high_low = df['High'] - df['Low'] color: #666; }
    
    .context-box { 
        padding: 10px
DB_CATEGORIES = {
    '🇦🇷 Argentina': ['GGAL', 'YPF', 'B
    high_close = np.abs(df['High'] - df['Close'].shift())
    low; border-radius: 5px; margin-bottom: 15px; 
        border-leftMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUP_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.: 4px solid #ccc; font-size: 0.9rem;
    }
    
concat([high_low, high_close, low_close], axis=1)
    true_range =V', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

    .alert-tag {
        font-size: 0.75rem; font-weight: bold# --- ALERTAS VISUALES ---
def get_rsi_alert(rsi):
    if rsi >', 'GLOB', 'MELI', 'BIOX'],
    '🇺🇸 Mag 7 & Tech': ['; padding: 4px 8px; 
        border-radius: 4px; margin-top: 6 70: return "⚠️ SOBRECOMPRA (Riesgo Corrección)", "#FFEBEE", "#AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSpx; display: inline-block;
    }
</style>
""", unsafe_allow_html=TrueLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO',C62828" 
    if rsi < 30: return "♻️ SOBRE)

# --- BASE DE DATOS MAESTRA ---
DB_CATEGORIES = {
    '🇦🇷 'PLTR'],
    '🤖 Semis & AI': ['AMD', 'INTC', 'QCOM',VENTA (Posible Rebote)", "#E8F5E9", "#2E7D32" Argentina': ['GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CE 
    if 40 <= rsi <= 65: return "✅ TENDENCIA SANA", 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCIPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'TSM', 'ASML'],
    '🏦 Financiero': ['JPM', 'BAC', ' "#E3F2FD", "#1565C0" 
    return "⚖️ NEUTRAL', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX'],C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BR", "#F5F5F5", "#616161"

def get_atr_alert
    '🇺🇸 Mag 7 & Tech': ['AAPL', 'MSFT', 'NVDA', 'GOK-B', 'PYPL', 'SQ', 'COIN'],
    '💊 Salud': ['LLY',(atr, price):
    atr_pct = (atr / price) * 100
    ifOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL atr_pct > 3.5: return f"⚡ VOLATILIDAD ALTA ({atr_pct:. 'NVO', 'JNJ', 'PFE', 'MRK', 'ABBV', 'UNH',', 'ADBE', 'IBM', 'CSCO', 'PLTR'],
    '🤖 Semis & AI 'BMY', 'AMGN'],
    '🛒 Consumo': ['KO', 'PEP', 'MCD1f}%)", "#FFF3E0", "#EF6C00"
    if atr_pct': ['AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', ' < 1.5: return f"🐢 VOLATILIDAD BAJA ({atr_pct:.1f}', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT',ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML'],
    '%)", "#F3E5F5", "#6A1B9A"
    return f"✨ 'HD', 'PG'],
    '🏭 Industria': ['XOM', 'CVX', 'SLB',🏦 Financiero': ['JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', VOLATILIDAD NORMAL ({atr_pct:.1f}%)", "#E0F2F1", "# 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'F', 'GM 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', '00695C"

# --- MOTOR DE CÁLCULO ---

def detect_region_benchmark'],
    '🇧🇷 Brasil': ['PBR', 'VALE', 'ITUB', 'BBD',COIN'],
    '💊 Salud': ['LLY', 'NVO', 'JNJ', 'PFE', 'ERJ', 'ABEV'],
    '🇨🇳 China': ['BABA', 'JD', 'BID(ticker):
    if ticker in DB_CATEGORIES['🇦🇷 Argentina']: return 'ARGT', "ETF 'MRK', 'ABBV', 'UNH', 'BMY', 'AMGN'],
    '🛒 Argentina"
    if ticker in DB_CATEGORIES['🇧🇷 Brasil']: return 'EWZ', "ETF BrasilU', 'PDD', 'NIO'],
    '⛏️ Minería': ['GOLD', 'NEM Consumo': ['KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'FCX', 'SCCO'],
    '📈 ETFs': ['SPY', 'QQQ', '"
    if ticker in DB_CATEGORIES['🇨🇳 China']: return 'FXI', "ETF China"', 'WMT', 'COST', 'TGT', 'HD', 'PG'],
    '🏭 Industria':IWM', 'DIA', 'EEM', 'EWZ', 'XLE', 'XLF', 'XL ['XOM', 'CVX', 'SLB', 'BA', 'CAT', 'DE', 'GE',
    if ticker in DB_CATEGORIES['🤖 Semis & AI']: return 'SOXX', "ETF SemK', 'XLV', 'ARKK', 'GLD', 'SLV', 'GDX']
}
CEDEAR_DATABASE = 'MMM', 'LMT', 'F', 'GM'],
    '🇧🇷 Brasil': ['PBR', sorted(list(set([item for sublist in DB_CATEGORIES.values() for item in sublist]))) 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV'],
    '🇨

# --- ESTADO (V11) ---
if 'st360_db_v11' not in st.session_state: st.session_state['st360_db_v1🇳 China': ['BABA', 'JD', 'BIDU', 'PDD', 'NIO'],
    '⛏️ Minería': ['GOLD', 'NEM', 'FCX', 'SCCO'],
    '📈 ETFs': ['SPY1'] = []

# --- HELPERS ---
def calculate_rsi(series, period=14):
', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'XLE',    delta = series.diff()
    gain = (delta.where(delta > 0, 0)). 'XLF', 'XLK', 'XLV', 'ARKK', 'GLD', 'SLV',rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0is"
    if ticker in DB_CATEGORIES['⛏️ Minería']: return 'GDX', "ETF Oro"
    return 'SPY', "S&P 500"

def get_market_ 'GDX']
}
CEDEAR_DATABASE = sorted(list(set([item for sublist in DB_CATEGORIES.)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
context_dynamic(ticker):
    try:
        bench_tk, bench_name = detect_region_    high_low = df['High'] - df['Low']
    high_close = np.abs(values() for item in sublist])))

# --- ESTADO (V11 - Limpieza de caché) ---
if 'st360_db_v11' not in st.session_state: st.session_state['stdf['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close,360_db_v11'] = []

# --- HELPERS MATEMÁTICOS ---
benchmark(ticker)
        data = yf.Tickers(f"{bench_tk} ^VIX")
        bench = data.tickers[bench_tk].history(period="6mo")
        vix = low_close], axis=1)
    true_range = np.max(ranges, axis=1)def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = data.tickers['^VIX'].history(period="5d")
        
        if bench.empty: return "NEUTRAL", f"Sin datos {bench_name}", 0, "N/A", bench_name
        
        price = bench['Close'].iloc[-1]
        ma50 = bench['Close'].rolling(50).mean().iloc[-1]
        vix_p = vix['Close'].iloc[-1] if not vix.empty else 0
        
        stt = "BULLISH" if price > ma50 else "BEARISH"
        msg = f"{'✅ Alcista' if price > ma50 else '🛑 Bajista'} en {bench_name}"
        vix_st = "🟢 Calma" if vix_p < 20 else "🔴 MIEDO" if vix_p >
    return true_range.rolling(period).mean()

# --- ALERTAS VISUALES ---
def (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where 25 else "🟡 Alerta"
        
        return stt, msg, vix_p, vix get_rsi_alert(rsi):
    if rsi > 70: return "⚠️ SOBRECOMP(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss_st, bench_name
    except: return "NEUTRAL", "Error Macro", 0, "N
    return 100 - (100 / (1 + rs))

def calculate_atr(RA (Riesgo Corrección)", "#FFEBEE", "#C62828"
    if rsi < 30:/A", "SPY"

def get_technical_score(df):
    try:
        scoredf, period=14):
    high_low = df['High'] - df['Low']
     return "♻️ SOBREVENTA (Posible Rebote)", "#E8F5E9", "#2 = 0; details = []
        
        # 1. HA Matrix (3 pts)
        ha_close = (E7D32"
    if 40 <= rsi <= 65: return "✅ Thigh_close = np.abs(df['High'] - df['Close'].shift())
    low_closeENDENCIA SANA", "#E3F2FD", "#1565C0"
    return " = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([df['Open']+df['High']+df['Low']+df['Close'])/4
        ha_open =⚖️ NEUTRAL", "#F5F5F5", "#616161"

def get (df['Open'].shift(1)+df['Close'].shift(1))/2
        daily_green =high_low, high_close, low_close], axis=1)
    true_range = np. ha_close.iloc[-1] > ha_open.iloc[-1]
        
        df_w_atr_alert(atr, price):
    atr_pct = (atr / price) * 10max(ranges, axis=1)
    return true_range.rolling(period).mean()

# --- = df.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':' ALERTAS VISUALES ---
def get_rsi_alert(rsi):
    if rsi > 7last'})
        ha_close_w = (df_w['Open']+df_w['High']+df0
    if atr_pct > 3.5: return f"⚡ VOLATILIDAD ALTA ({atr_pct:.1f}%)", "#FFF3E0", "#EF6C00"
    if atr_pct < 1_w['Low']+df_w['Close'])/4
        ha_open_w = (df_0: return "⚠️ SOBRECOMPRA (Riesgo)", "#FFEBEE", "#C62828"
    .5: return f"🐢 VOLATILIDAD BAJA ({atr_pct:.1f}%)", "#if rsi < 30: return "♻️ SOBREVENTA (Rebote?)", "#E8F5E9w['Open'].shift(1)+df_w['Close'].shift(1))/2
        w_greenF3E5F5", "#6A1B9A"
    return f"✨ VOLATIL = ha_close_w.iloc[-1] > ha_open_w.iloc[-1] if not", "#2E7D32"
    if 40 <= rsi <= 65: returnIDAD NORMAL ({atr_pct:.1f}%)", "#E0F2F1", "#006 "✅ TENDENCIA SANA", "#E3F2FD", "#1565C0"
 df_w.empty else False
        
        df_m = df.resample('ME').agg({'95C"

# --- MOTOR DE CÁLCULO ---
def detect_region_benchmark(ticker):
    if ticker in DB_    return "⚖️ NEUTRAL", "#F5F5F5", "#616161"Open':'first','High':'max','Low':'min','Close':'last'})
        ha_close_m =CATEGORIES['🇦🇷 Argentina']: return 'ARGT', "ETF Argentina"
    if ticker in DB_CATEG (df_m['Open']+df_m['High']+df_m['Low']+df_m['Close'])/4
        ha_open_m = (df_m['Open'].shift(1)+df_

def get_atr_alert(atr, price):
    atr_pct = (atr / price) * 100
    if atr_pct > 3.5: return f"⚡ VOLATILIDADm['Close'].shift(1))/2
        m_green = ha_close_m.iloc[-1] > ha_open_m.iloc[-1] if not df_m.empty else False

        if daily_green: score+=1; details.append("HA Diario Alcista")
        if w_green: score+=1; details.append("HA Semanal Alcista")
        if m_green: score+=1; details.append("HA Mensual Alcista")

        # 2. Medias (5 pts)
        price = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma50 = df['Close'].rolling(50).mean().iloc[-1 ALTA ({atr_pct:.1f}%)", "#FFF3E0", "#EF6C00"
    if atr_pct < 1.5: return f"🐢 VOLATILIDAD BAJA ({atr_pct:.1f}%)", "#F3E5F5", "#6A1B9A"
    return f"✨ VOLATILIDAD NORMAL ({atr_pct:.1f}%)", "#E0F2F1", "#00695C"

# --- MOTOR DE CÁLCULO ---

def detect_region_benchmark(ticker):
    if ticker in DB_CATEGORIES['🇦🇷 Argentina']: return 'ARGT', "ETF Argentina"
    if ticker in DB_CATEGORIES['🇧🇷 Brasil']: return]
        ma200 = df['Close'].rolling(200).mean().iloc[-1]
        
        if price > ma20: score+=1; details.append("> MA20")
        if ma20 > ma50: score+=2; details.append("MA20 > MA5 'EWZ', "ETF Brasil"
    if ticker in DB_CATEGORIES['🇨🇳 China']: return 'FXI', "ETF China"
    if ticker in DB_CATEGORIES['🤖 Semis & AI']: return 'SOXX', "ETF Semis"
    if ticker in DB_CATEGORIES['⛏️ Minería']: return 'GDXORIES['🇧🇷 Brasil']: return 'EWZ', "ETF Brasil"
    if ticker in DB_CATEGORIES['🇨🇳 China']: return 'FXI', "ETF China"
    if ticker in DB_CATEGORIES['🤖 Semis & AI']: return 'SOXX', "ETF Semis"
    if ticker in DB_CATEGORIES['⛏️ Minería']: return 'GDX', "ETF Oro"
    return 'SPY', "S&P 500"

def get_market_context_dynamic(ticker):
    try:
        bench_tk, bench_name = detect_region_benchmark(ticker)
        data = yf.Tickers(f"{bench_tk} ^VIX")
        bench = data.tickers[bench_tk].history(period="6mo")
        vix = data.tickers['^VIX'].history(period="5d")
        
        if bench.empty: return "NEUTRAL", f"Sin datos {bench_name}", 0, "N/A", bench_name
        
        price = bench['Close'].iloc[-1]
        ma50 = bench['Close'].rolling(50).mean().iloc[-1]
        vix_p = vix['Close'].iloc[-1] if not vix.empty else 0
        
        stt = "BULLISH" if price > ma50 else "BEARISH"
        msg = f"{'✅ Alcista' if price > ma50 else '🛑 Bajista'} en {bench_name}"
        vix_st = "🟢 Calma" if vix_p < 20 else "🔴 MIEDO" if vix_p > 25 else "🟡 Alerta"
        
        return stt, msg, vix_p, vix_st, bench_name
    except: return "NEUTRAL", "Error Macro", 0, "N/A", "SPY"

def get_technical_score(df):
    try:
        score = 0; details = []
        # HA Matrix
        ha_close = (df['Open']+df['High']+df['Low']+df['Close'])/4
        ha_open = (df['Open'].shift(1)+df['Close'].shift(1))/2
        if ha_close.iloc[-1] > ha_open.iloc[-1]: score+=1; details.append("HA Diario Alcista")
        else: details.append("HA Diario Bajista")
        
        df_w = df.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last'})
        ha_cw = (df_w['Open']+df_w['High']+df_w['Low']+df_w['Close'])/4
        ha_ow = (df_w['Open'].shift(1)+df_w['Close'].shift(1))/2
        if not df_w.empty and ha_cw.iloc[-1] > ha_ow.iloc[-1]: score+=1; details.append("HA Semanal Alcista")
        else: details.append("HA Semanal Bajista")
        
        # Al0")
        if price > ma200: score+=2; details.append("> MA200")

        # 3. RSI (2 pts)
        rsi = calculate_rsi(df['Close']).iloc[-1]
        if 40 <= rsi <= 65: score += 2 
        elif rsi > 70: score -= 2
        elif rsi < 30: score += 1
            
        return max(0, min(10, score)), details, rsi
    except: return 0, ["Error"], 50

def get_options_data(ticker, price):
    def_res = (5, "Sin Opciones", 0, 0, 0, "N/A", 0)
    try:
        tk = yf.Ticker(ticker)
        try: exps = tk.options
        except: return def_res
        if not exps: return def_res
        
        opt = tk.option_chain(exps[0])
        calls = opt.calls; puts = opt.puts
        if calls.empty or puts.empty: return def_res
        
        # --- SENTIMIENTO MEJORADO ---
        total_call = calls['openInterest'].sum()
        total_put = puts['openInterest'].sum()
        pcr = total_put / total_call if total_call > 0 else 0
        
        # Etiquetas de Alerta
        if pcr < 0.6: sentiment = "🚀 EUFORIA (Alerta: Exceso Optimismo)"
        elif pcr > 1.4: sentiment = "🐻 MIEDO EXTREMO (Alerta: Piso?)"
        else: sentiment = "⚖️ NEUTRAL (Flujo Balanceado)"

        # Muros
        cw = calls.loc[calls['openInterest'].idxmax()]['strike']
        pw = puts.loc[puts['openInterest'].idxmax()]['strike']
        
        strikes = sorted(list(set(calls['strike'].tolist() + puts['strike'].tolist())))
        rel = [s for s in strikes if price*0.7 < s < price*1.3] or strikes
        cash = []
        for s in rel:
            c_loss = calls.apply(lambda r: max(0, s-r['strike'])*r['openInterest'], axis=1).sum', "ETF Oro"
    return 'SPY', "S&P 500"

def get_market_context_dynamic(ticker):
    try:
        bench_tk, bench_name = detect_region_benchmark(ticker)
        data = yf.Tickers(f"{bench_tk} ^VIX")
        bench = data.tickers[bench_tk].history(period="6mo")
        vix = data.tickers['^VIX'].history(period="5d")
        
        if bench.empty: return "NEUTRAL", f"Sin datos {bench_name}", 0, "N/A", bench_name
        
        price = bench['Close'].iloc[-1]
        ma50 = bench['Close'].rolling(50).mean().iloc[-1]
        vix_p = vix['Close'].iloc[-1] if not vix.empty else 0
        
        stt = "BULLISH" if price > ma50 else "BEARISH"
        msg = f"{'✅ Alcista' if price > ma50 else '🛑 Bajista'} en {bench_name}"
        vix_st = "🟢 Calma" if vix_p < 20 else "🔴 MIEDO" if vix_p > 25 else "🟡 Alerta"
        
        return stt, msg, vix_p, vix_st, bench_name
    except: return "NEUTRAL", "Error Macro", 0, "N/A", "SPY"

def get_technical_score(df):
    try:
        score = 0; details = []
        
        # 1. HA Matrix (3 pts)
        ha_close = (df['Open']+df['High']+df['Low']+df['Close'])/4
        ha_open = (df['Open'].shift(1)+df['Close'].shift(1))/2
        daily_green = ha_close.iloc[-1] > ha_open.iloc[-1]
        
        df_w = df.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last'})
        ha_close_w = (df_w['Open']+df_w['High']+df_w['Low']+df_w['Close'])/4
        ha_open_w = (df_w['Open'].shift(1)+df_w['Close'].shift(1))/2
        weekly_green = ha_close_w.iloc[-1] > ha_open_w.iloc[-1] if not df_w.empty else False

        if daily_green: score+=1; details.append("HA Diario Alcista")
        else: details.append("HA Diario Bajista")
         menos 2 de 3 temporalidades alcistas = 1 punto extra (Bonus Matrix)
        if score >= 2: score += 1

        # Medias
        price = df['Close'].iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma50 = df['Close'].rolling(50).mean().iloc[-1]
        
        if price > ma20: score+=2; details.append("> MA20")
        if ma20 > ma50: score+=3()
            p_loss = puts.apply(lambda r: max(0, r['strike']-s)*r['openInterest'], axis=1).sum()
            cash.append(c_loss+p_loss)
        mp = rel[np.argmin(cash)] if cash else price

        # Score
        score = 5
        detail = "Rango Medio"
        if price > cw: score=10; detail="🚀 Breakout Gamma"
        elif price < pw: score=1; detail="💀 Breakdown Gamma"
        else:
            rng = cw - pw
            if rng > 0:
                pos = (price - pw)/if weekly_green: score+=1; details.append("HA Semanal Alcista")
        else: details.append("HA Semanal Bajista")
        if daily_green and weekly_green: score+=1

        # 2. Medias (5 pts)
        price = df['Close'].iloc[-1]
; details.append("Tendencia Sana (MA20>50)")
        
        # RSI
        rsi = calculate_rsi(df['Close']).iloc[-1]
        if 40 <= rsi <= 65: scorerng
                score = 10 - (pos*10)
                if score > 8: detail="🟢 Soporte (PW)"
                elif score < 2: detail="🧱 Resistencia (CW)"
                else: detail=f"Rango ${pw}-${cw}"
                
        return score, detail, cw, pw, mp, sentiment, pcr
    except: return def_res

def get_seasonality_score(df):
    try:
        curr_month = datetime.now().month
        m_ret = df['Close'].resample('ME').last().pct_change()
        hist = m_ret[m_ret.index.month == curr_month]
        if len(hist) < 2: return 5, "Sin Historia", 0
        
        win = (hist > 0).mean()
        avg = hist.mean()
        
        score = win * 6
        if avg > 0.01: score += 4
        elif avg > 0: score += 2
        else: score -= 2
        
        wins = hist[hist>0]; losses = hist[hist<0]
        avg_w = wins.mean() if not wins.empty else 0
        avg_l = abs(losses.mean()) if not losses.empty else 0
        
        warning = ""
        if avg_l > (avg_w * 2) and avg_l >         ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma50 = df['Close'].rolling(50).mean().iloc[-1]
        ma200 = df['Close'].rolling(200).mean().iloc[-1]
        
        if price > ma20: score+=1; details.append("> MA20")
        if ma20 > ma50: score+=2; details.append("MA20 > MA50")
        if price > ma200: score+=2; details.append("> MA200")

        # 3. RSI (2 pts)
        rsi = calculate_rsi(df['Close']).iloc[-1]
        if 40 <= rsi <= 65: score += 2 
        elif rsi > 70: score -= 2
        elif rsi < 30: score += 1
            
        return max(0, min(10, score)), details, rsi
    except: return 0, ["Error"], 50

def get_options_data(ticker, price):
    # Default
    def_res = (5, "Sin Opciones", 0, 0, 0, "N/A", 0)
    try:
        tk = yf.Ticker(ticker)
        try: exps = tk.options
        except: return def_res
        if not exps: return def_res
        
        opt = tk.option_chain(exps += 2
        elif rsi > 70: score -= 2
        elif rsi < 30: score += 1
        
        return max(0, min(10, score)), details, rsi
    except: return 0, ["Error"], 50

def get_options_data(ticker, price):
    def_res = (5, "Sin Opciones", 0, 0, 0, "N/A", 0)
    try:
        tk = yf.Ticker(ticker)
        try: exps = tk.options
        except: return def_res
        if not exps: return def_res
        opt = tk.option_chain(exps[0])
        calls, puts = opt.calls, opt.0.03:
            score -= 3; warning = "⚠️ RIESGO (Loss > 2x Win)"
            
        return max(0, min(10, score)), f"WR: {win:.0%} | {warning}", avg
    except: return 5, "N/A", 0

def analyze_complete(ticker):
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period="2y")
        if df.empty: return None
        price[0])
        calls = opt.calls; puts = opt.puts
        if calls.empty or puts.empty: return def_res
        
        # SENTIMIENTO MEJORADO
        t_call = calls['openInterest'].sum()
        t_put = puts['openInterest'].sum()
        pcr = t_put / t_call if t_call > 0 else 0
        
        if pcr < 0.6: 
            sentiment = "🚀 EUFORIA (Alerta: Techo?)"
        elif pputs
        if calls.empty or puts.empty: return def_res
        
        # --- SENTIMIENTO MEJORADO ---
        total_call = calls['openInterest'].sum()
        total_put = puts['openInterest'].sum()
        pcr = total_put / total_call if total_call > 0 else 0
        
        if pcr < 0.6: sentiment = "🚀 EUFORIA (Alerta: Techo)"
        elif pcr > 1.4: sentiment = "🐻 MIEDO (Posible Piso)"
        else: sentiment = "⚖️ NEUTRAL"

        cw = calls.loc[calls['openInterest'].idxmax()]['strike']
        pw = puts.loc[puts['openInterest'].idxmax()]['strike']
        
        strikes = sorted(list(set(calls['strike'].tolist()+puts['strike'].tolist())))
        rel = [s for s in strikes if price*0.7 < s < price*1.3] or = df['Close'].iloc[-1]
        
        # 1. Técnico
        s_tec, d_tec_list, rsi = get_technical_score(df)
        d_tec_strcr > 1.4: 
            sentiment = "🐻 MIEDO (Alerta: Piso?)"
         strikes
        cash = []
        for s in rel:
            c_loss = calls.apply(lambda r: max(0, s-r['strike'])*r['openInterest'], axis=1).sum()
             = ", ".join([d for d in d_tec_list if "(+" in d or "RSI" in d])
        
        # 2. Opciones (Nueva devolución de valores)
        s_opt, d_opt, cw, pw, mp, sent, pcr_val = get_options_data(ticker, price)
        
        # 3. Estacionalidad
        s_sea, d_sea, avg_ret = get_seasonality_score(df)
        
        # 4. Niveles
        atr, sl, tp = calculate_levels(df, price)
        
        # 5. Contexto
        macro_st, macro_msg, vix, vix_st, bench = get_market_context_dynamic(ticker)
        
        final = (s_tec * 4) + (s_opt * 3) + (s_sea * 3)
        if macro_st == "BEARISH": final -= 10
        if vix > 25: final -= 5
        
        verdict = "NEUTRAL"
        if final >= 75: verdict = "🔥 COMPRA FUERTE"
        elif final >= 60: verdict = "✅ COMPRA"
        elif final <= 25: verdict = "💀 VENTA FUERTE"
        elif final <= 40: verdict = "🔻 VENTA"
        
        return {
            "Ticker": ticker, "Price": price, "Score": final, "Verdict": verdict,
            "S_Tec": s_tec, "D_Tec_List": d_tec_list, "RSI": rsi,
            "S_Opt": s_opt, "D_Opt": d_opt, "Sentiment": sent, "PCR": pcr_val,
            "S_Sea": s_sea, "D_Sea": d_sea,
            "CW": cw, "PW": pw, "Max_Pain": mp,
            "ATR": atr, "SL": sl, "TP": tp,
            "Macro_Msg": macro_msg, "Bench": bench, "VIX": vix, "VIX_St": vix_st,
            "History": df
        }
    except: return None

# --- UI ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    st.info(f"Base de Datos: {len(CEDEAR_DATABASE)} Activos")
    
    batch_size = st.slider("Tamaño del Lote", 1, 15, 5)
    batches = [CEDEAR_DATABASE[i:else: 
            sentiment = "⚖️ NEUTRAL (Sano)"

        # Muros
        cw = calls.loc[calls['openInterest'].idxmax()]['strike']
        pw = puts.loc[puts['openInterest'].idxmax()]['strike']
        
        strikes = sorted(list(set(calls['strike'].tolist() + puts['strike'].tolist())))
        rel = [s for s in strikes if price*0.7 < s < price*1.3] or strikes
        
        cash = []
        for s in rel:
            c_loss = calls.apply(lambda r: max(0, s-r['strike'])*r['openInterest'], axis=1).sum()
            p_loss = puts.apply(lambda r: max(0, r['strike']-s)*r['openInterest'], axis=1).sum()
            cash.append(c_loss+p_loss)
        mp = rel[np.argmin(cash)] if cash else price

        # Score
        score = 5
        detail = "Rango Medio"
        if price > cw: score=10; detail="🚀 Breakout Gamma"
        elif price < pw: score=1; detail="💀 Breakdown Gamma"
        else:
            rng = cw - pw
            if rng > 0:
                pos = (price - pw)/rng
                score = 10 - (pos*10)
                if score > 8: detail="🟢 Soporte (PW)"
                elif score < 2: detail="🧱 Resistencia (CW)"
                else: detail=f"Rango ${pw}-${cw}"
                
        return score, detail, cw, pw, mp, sentiment, pcr
    except: return def_res

def get_seasonality_score(df):
    try:
        curr_m = datetime.now().month
        m_ret = df['Close'].resample('ME').last().pct_change()
        hist = m_ret[m_ret.index.month == curr_m]
        
        if len(hist) < 2: return 5, "Sin Historia", 0
        
        win = (hist > 0).mean()
        avg = hist.mean()
        
        score = win * 6
        if avg > 0.01: score += 4
        elif avg > 0: score += 2
        else: score -= 2
        
        # Anti-Aplanadora
        wins = hist[hist>0]; losses = hist[hist<0]
        p_loss = puts.apply(lambda r: max(0, r['strike']-s)*r['openInterest'], axis=1).sum()
            cash.append(c_loss+p_loss)
        mp = rel[np.argmin(cash)] if cash else price

        score = 5
        detail = "Rango Medio"
        if price > cw: score=10; detail="🚀 Breakout Gamma"
        elif price < pw: score=1; detail="💀 Breakdown Gamma"
        else:
            rng = cw - pw
            if rng > 0:
                pos = (price - pw)/rng
                score = 10 - (pos*10)
                if score > 8: detail="🟢 Soporte (PW)"
                elif score < 2: detail="🧱 Resistencia (CW)"
                else: detail=f"Rango ${pw}-${cw}"
                
        return score, detail, cw, pw, mp, sentiment, pcr
    except: return def_res

def get_seasonality_score(df):
    try:
        curr_m = datetime.now().month
        m_ret = df['Close'].resample('ME').last().pct_change()
        hist = m_ret[m_ret.index.month == curr_m]
        
        win = (hist>0).mean() if len(hist)>1 else 0
        score = win * 6
        avg = hist.mean() if len(hist)>1 else 0
        
        if avg > 0.01: score += 4
        elif avg > 0: score += 2
        else: score -= 2
        
        # Anti-Aplanadora
        wins = hist[hist>0]; losses = hist[hist<0]
        avg_w = wins.mean() if not wins.empty else 0
        avg_l = abs(losses.mean()) if not losses.empty else 0
        
        warning = ""
        if avg_l > (avg_w * 2) and avg_l > 0.03:
            score -= 3; warning = "⚠️ RIESGO (Loss > 2x Win)"
            
        return max(0, min(10, score)), f"WR: {win:.0%} | {warning}", avg
    except: return 5, "N/A", 0

def analyze_complete(ticker):
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period="2y")
        if df.empty: return None
        price = df['Close'].iloc[-1]
        
        s_teci + batch_size] for i in range(0, len(CEDEAR_DATABASE), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionaravg_w = wins.mean() if not wins.empty else 0
        avg_l = abs(losses.mean()) if not losses.empty else 0
        
        warning = ""
        if avg_l > (avg_w * 2) and avg_l > 0.03:
            score, d_tec_list, rsi = get_technical_score(df)
        d_tec_str = ", ".join([d for d in d_tec_list if "(+" in d or "RSI Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("▶️ ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        prog = st.progress(0)
        mem = [x['Ticker'] for x in st.session_state['st360_db_v11']]
        run = [t for t in targets if t not in mem]
        for i, t in enumerate(run):
            r = analyze_complete(t)
            if r: st.session_state['st360_db_v11'].append(r)
            prog.progress((i+1)/len(run))
            time.sleep(0.3)
        prog.empty(); st -= 3; warning = "⚠️ RIESGO (Loss > 2x Win)"
            
        return max(0, min(10, score)), f"WR: {win:.0%} | {warning}", avg
    except: return 5, "N/A", 0

def analyze_complete(ticker):
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period="2y")
        if df.empty: return None
        price = df['Close'].iloc[-1]
        
        s_tec, d_tec_list, rsi = get_technical_score(df)
        d_tec_str = ", ".join([d for d in d_tec_list if "(+" in d or "RSI" in d])
        
        # Desempaquetamos PCR y" in d])
        
        s_opt, d_opt, cw, pw, mp, sent, pcr_val = get_options_data(ticker, price)
        
        s_sea, d_sea, avg_ret = get_seasonality_score(df)
        atr, sl, tp = calculate_levels(df, price)
        
        # Contexto
        macro_st, macro_msg, vix, vix_st, bench = get_market_context_dynamic(ticker)
        
        final = (s_tec * 4) + (s_opt * 3) + (s_sea * 3)
        if macro_st == "BEARISH": final -= 10
        if vix > 25: final -= 5
        
        verdict = "NEUTRAL"
        if final >= .rerun()
        
    if c2.button("🗑️ Limpiar"): st.session_state['st360_db_v11'] = []; st.rerun()
    st.divider()
    mt = st.text_input("Ticker Manual:").upper().strip()
    if st.button("Analizar"):
        if mt:
            with st.spinner("Procesando..."):
                r = analyze_complete(mt)
                if r:
                    st.session_state['st360_db_v11'] = [x for x in st.session_state['st360_db_v11'] if x['Ticker']!=mt]
                    st.session_state['st360_db_v11'].append(r)
                    st.rerun()

st.title("SystemaTrader 360: Final Edition")

if st.session_state['st360_db_v11']:
    dfv = pd.DataFrame(st.session_state['st Sentimiento nuevo
        s_opt, d_opt, cw, pw, mp, sent, pcr = get_options_data(ticker, price)
        
        s_sea, d_sea, avg_ret = get_seasonality_score(df)
        atr, sl, tp = calculate_levels(df, price)
        
        macro_st, macro_msg, vix, vix_st, bench = get_market_context_dynamic(ticker)
        
        final = (s_tec * 4) + (s_opt * 3) + (s_sea * 3)
        if macro_st == "BEARISH": final -= 10
        if vix > 25: final -= 5
        
        verdict = "NEUTRAL"
        if final >= 75: verdict = "🔥 COMPRA FUERTE"
        elif final >= 60: verdict = "✅ COMPRA"
        elif final <= 25: verdict = "💀 VENTA FUERTE"
        elif final <= 40: verdict =75: verdict = "🔥 COMPRA FUERTE"
        elif final >= 60: verdict = "✅ COMPRA"
        elif final <= 25: verdict = "💀 VENTA FUERTE"
        elif final <= 40: verdict = "🔻 VENTA"
        
        return {
            "Ticker": ticker, "Price": price, "Score": final, "Verdict": verdict,
            "S_Tec": s_tec, "RSI": rsi,
            "S_Opt": s_opt, "Sentiment": sent, "PCR": pcr_val,
            "CW": cw, "PW": pw, "Max_Pain": mp,
            "S_Sea": s_sea, "Avg_Ret": avg_ret,
            "ATR": atr, "SL": sl, "TP": tp,
            "Macro_Msg": macro_msg, "Bench": bench, "VIX": vix, "VIX_St": vix_st,
            "History": df, "D_Tec_List": d_tec_list, "D_Opt360_db_v11'])
    if 'Score' in dfv.columns: dfv = dfv.sort_values("Score", ascending=False)
    
    st.dataframe(
        dfv[['Ticker', 'Price', 'Score', 'Verdict', 'S_Tec', 'S_Opt', 'S_Sea']],
        column_config={
            "Ticker": "Activo", "Price": st.column_config.NumberColumn "🔻 VENTA"
        
        return {
            "Ticker": ticker, "Price": price, "Score": final, "Verdict": verdict,
            "S_Tec": s_tec, "RSI": rsi, "D_Tec_List": d_tec_list,
            "S_Opt": s_opt, "Sentiment": sent, "PCR": pcr, "CW": cw, "PW": pw,": d_opt, "D_Sea": d_sea
        }
    except: return None

# --- UI ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    st.info(f"Base de Datos: {len(CEDEAR_DATABASE)} Activos")
    
    batch_size = st.slider("Tamaño del Lote", 1, 15, 5)(format="$%.2f"),
            "Score": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=100, format="%.0f"),
            "S_Tec": st.column_config.NumberColumn("Técnico", format="%.1f"),
            "S_Opt": st.column_config.NumberColumn("Opciones", format="%.1f"),
            "S_Sea": st.column_config.NumberColumn("Estac.", format="%.1f")
        }, use_container_width=True, hide_index=True
    )
    
     "Max_Pain": mp, "D_Opt": d_opt,
            "S_Sea": s_sea, "D_Sea": d_sea, "Avg_Ret": avg_ret,
            "ATR": atr, "SL": sl, "TP": tp,
            "Macro_Msg": macro_msg, "Bench": bench, "VIX": vix, "VIX_St": vix_st,
            "History": df
        }
    except: return None

def calculate_levels(df, price):
    try:
        atr = calculate_atr(df).iloc[-1]
        sl = price - (2 * atr)
        tp
    batches = [CEDEAR_DATABASE[i:i + batch_size] for i in range(0, len(CEDEAR_DATABASE), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("▶️ ESCANEAR", type="primary"):
        targets = batches[sel_batch]
st.divider()
    sel = st.selectbox("Inspección Profunda:", dfv['Ticker'].tolist())
    it = next((x for x in st.session_state['st360_db_v11'] if x['Ticker'] == sel), None)
    
    if it:
        # Generar Alertas Visuales
        rsi_msg, rsi_bg, rsi_txt = get_rsi_alert(it['RSI'])
        atr_msg, atr_bg, atr_txt = get_atr_alert(it['ATR'], it['Price'])
        
        # Alerta de Sentimiento (Colores Lógicos)
        sent_bg = "# = price + (3 * atr)
        return atr, sl, tp
    except: return 0, 0, 0

# --- UI ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    st.info(f"Base de Datos: {len(CEDEAR_DATABASE)} Activos")
    
    batch_size = st.slider("Tamaño del Lote", 1, 15, 5)
    batches = [CEDEAR_DATABASE[i:i + batch_size] for i in range(0, len(CEDEAR_DATABASE), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches        prog = st.progress(0)
        mem = [x['Ticker'] for x in st.session_state['st360_db_v11']]
        run = [t for t in targets if t not in mem]
        for i, t in enumerate(run):
            r = analyze_complete(t)
            if r: st.session_state['st360_db_v11'].append(r)
            prog.progress((i+1)/len(run))
            time.sleep(0.3)
        prog.empty(); st.rerun()
        
    if c2.button("🗑️ Limpiar"): st.session_state['st360_db_v11']F5F5F5"; sent_txt = "#333"
        if "EUFORIA" in it['Sentiment']:
            sent_bg = "#FFEBEE"; sent_txt = "#C62828" # Rojo (Peligro Techo)
        elif "MIEDO" in it['Sentiment']:
            sent_bg = "#E8F5E9"; sent_txt = "#2E7D32" # Verde (Oportunidad Piso)
        
        # Banner Contexto
        clr_mc = "#d4edda")]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("▶️ ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        prog = st.progress(0)
        mem = [x['Ticker'] for x in st.session_state['st360_db_v11']]
         = []; st.rerun()
    st.divider()
    mt = st.text_input("Ticker Manual:").upper().strip()
    if st.button("Analizar"):
        if mt:
            with st.spinner("Procesando..."):
                r = analyze_complete(mt)
                if r:
                    st.session_state['st360_db_v11'] = [x for x in st.session_state['st360_db_v11'] if x['Ticker'] if "✅" in it['Macro_Msg'] else "#f8d7da"
        txt_mc = "#155724" if "✅" in it['Macro_Msg'] else "#721c24"
        
        st.markdown(f"""
        <div class="context-box" style="background-color: {clr_mc}; color: {txt_mc}; border-color: {txt_mc};">
            🌍 <b>CONTEXTO REGIONAL ({it['Bench']}):</b> {it['Macro_Msg']} | 📉 <b>VIX:</b> {it['VIX']:.2f} ({it['VIX_St']})
        </div>
        """, unsafe_allow_html=True)
        
        k1, k2, k3, k4 = st.columns(4)
        sc =run = [t for t in targets if t not in mem]
        for i, t in enumerate(run):
            r = analyze_complete(t)
            if r: st.session_state['st360_db_v11'].append(r)
            prog.progress((i+1)/len(run))
            time.sleep(0.3)
        prog.empty(); st.rerun()
        
    if c2.button("🗑️ Limpiar"): st.session_state['st360_db_v11'] = []; st.rerun()
    st.divider()
    mt = st.text_input("Ticker Manual:").upper().strip()
    if st.button("Analizar"):
        if mt:
            with st.spinner("Procesando..."):
                r = analyze_!=mt]
                    st.session_state['st360_db_v11'].append(r)
                    st.rerun()

st.title("SystemaTrader 360: Diamond Edition")

if st.session_state['st360_db_v11']:
    dfv = pd.DataFrame(st.session_state['st360_db_v11'])
    if 'Score' in dfv.columns: dfv = dfv.sort_values("Score", ascending=False)
    
    st.dataframe(
        dfv[['Ticker', 'Price', 'Score', 'Verdict', 'S_Tec', 'S_Opt', 'S_Sea']],
        column_config={
            "Ticker": "Activo", "Price": st.column_config.NumberColumn(format="$%.2 it['Score']
        clr = "#00C853" if sc >= 70 else "#D32F2F" if sc <= 40 else "#FBC02D"
        
        with k1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="score-label">TÉCNICO</div>
                <div class="big-score" style="color:#555;">{it['S_Tec']:.1f}</div>
                <div class="alert-tag" style="background-color:{rsi_bg}; color:{rsi_txt};">{rsi_msg}</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="metric-card" style="border: 2px solid {clr};">
                <div class="score-label" style="color:{clr};">PUNTAJE</div>
                <div class="big-score" style="color:{clr};">{sc:.0f}</div>
                <div style="font-weight:bold;complete(mt)
                if r:
                    st.session_state['st360_db_v11'] = [x for x in st.session_state['st360_db_v11'] if x['Ticker']!=mt]
                    st.session_state['st360_db_v11'].append(r)
                    st.rerun()

st.title("SystemaTrader 360: Platinum V2")

if st.session_state['st360_db_v11']:
    dfv = pd.DataFrame(st.session_state['st360_db_v11'])
    if 'Score' in dfv.columns: dfv = dfv.sort_values("Score", ascending=False)
    
    st.dataframe(
        dfv[['Ticker', 'Price', 'Score', 'Verdict', 'S_Tec', 'S_Opt', 'S_Sea']],
        column_config={
            "Ticker": "Activo", "Price": st.column_f"),
            "Score": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=100, format="%.0f"),
            "S_Tec": st.column_config.NumberColumn("Técnico", format="%.1f"),
            "S_Opt": st.column_config.NumberColumn("Opciones", format="%.1f"),
            "S_Sea": st.column_config.NumberColumn("Estac.", format="%.1f")
        }, use_container_width=True, hide_index=True
    )
    
    st.divider()
    sel = st.selectbox("Inspección Profunda:", dfv['Ticker'].tolist())
    it = next((x for x in st.session_state['st360_db_v11'] if x['Ticker'] == sel), None)
    
    if it:
        rsi_msg, rsi_bg, rsi_txt = get_rsi_alert(it['RSI'])
        atr_msg, atr_bg, atr_txt = get_atr_alert(it['ATR'], it['Price'])
 color:{clr};">{it['Verdict']}</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="score-label">ESTRUCTURA</div>
                <div class="big-score" style="color:#555;">{it['S_Opt']:.1f}</div>
                <div class="alert-tag" style="background-color:{sent_bg}; color:{sent_txt};">
                    {it['Sentiment']}
                </div>
            </div>""", unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="score-label">RIESGO</div>
                <div class="alert-tag" style="background-color:{atr_bg}; color:{atr_config.NumberColumn(format="$%.2f"),
            "Score": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=100, format="%.0f"),
            "S_Tec": st.column_config.NumberColumn("Técnico", format="%.1f"),
            "S_Opt": st.column_config.NumberColumn("Opciones", format="%.1f"),
            "S_Sea": st.column_config.NumberColumn("Estac.", format="%.1f")
        }, use_container_width=True, hide_index=True
    )
    
    st.divider()
    sel = st.selectbox("Inspección Profunda:", dfv['Ticker'].tolist())
    it = next((x for x in st.session_state['st36        
        # Colores de Sentimiento
        sent_bg = "#F5F5F5"; sent_txt = "#333"
        if "EUFORIA" in it['Sentiment']: sent_bg, sent_txt = "#FFEBEE", "#C62828"
        elif "MIEDO" in it['Sentiment']: sent_bg, sent_txt = "#E8F5E9", "#2E7D32"
        
        clr_mc = "#d4edda" if "✅" in it['Macro_Msg'] else "#f8d7da"
        txt_mc = "#155724" if "✅" in it['Macro_Msg'] else "#721c24"
        
        st.markdowntxt}; margin-bottom:5px;">{atr_msg}</div>
                <div style="text-align:left; font-size:0.85rem;">🎯 <b>TP:</b> ${it['TP']:.2f}<br>🛡️ <b>SL:</b> ${it['SL']:.2f}</div>
            </div>""", unsafe_allow_html=True)

        with st.expander("🔎 Auditoría Completa"):
            st.markdown(f"""
            **1. Análisis Técnico:**
            - Detalles: {', '.join(it['D_Tec_List'])}
            - RSI: {it['RSI']:.1f}
            
            **2. Estructura de Opciones:**
            - Sentimiento (Put/Call Ratio): {it['PCR']:.2f}
            - Muros: Put ${it['PW']:.2f} | Call ${it['CW']:.2f} | Max Pain ${0_db_v11'] if x['Ticker'] == sel), None)
    
    if it:
        # Generar Alertas
        rsi_msg, rsi_bg, rsi_txt = get_rsi_alert(it['RSI'])
        atr_msg, atr_bg, atr_txt = get_atr_alert(it['ATR'], it['Price'])
        
        # Color Sentimiento
        sent_bg = "#F5F5F5"; sent_txt = "#333"
        if "EUFORIA" in it['Sentiment']: sent_bg = "#FFEBEE"; sent_txt = "#C62828"
        elif "MIEDO" in it['Sentiment']: sent_bg = "#E8F5E9"; sent_txt = "#2E7D32"
        
        # Contexto
        clr_mc = "#d4edda" if "✅" in it['Macro_Msg'] else "#f8d7da"
        txt_mc = "#155724" if "✅" in it['Macro_Msg'](f"""
        <div class="context-box" style="background-color: {clr_mc}; color: {txt_mc}; border-color: {txt_mc};">
            🌍 <b>CONTEXTO REGIONAL ({it['Bench']}):</b> {it['Macro_Msg']} | 📉 <b>VIX:</b> {it['VIX']:.2f} ({it['VIX_St']})
        </div>
        """, unsafe_allow_html=True)
        
        k1, k2, k3, k4 = st.columns(4)
        sc = it['Score']
        clr = "#00C853" if sc >= 70 else "#D32F2F" if sc <= 40 else "#FBC02D"
        
        with k1:
            st.markdown(f"""<div class="metric-card"><div class="score-label">TÉCNICO</div><div class="bigit['Max_Pain']:.2f}
            - Diagnóstico: {it['D_Opt']}
            
            **3. Estacionalidad Financiera:**
            - {it['D_Sea']}
            """)
            
        h = it['History']
        fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name='Precio')])
        if it['SL'] > 0:
            fig.add_hline(y=it['SL'], line_dash="solid", line_color="red", annotation_text="STOP")
            fig.add_hline(y=it['TP'], line_dash="solid", line_color="green", annotation_text=" else "#721c24"
        
        st.markdown(f"""
        <div class="context-box" style="background-color: {clr_mc}; color: {txt_mc}; border-color: {txt_mc};">
            🌍 <b>CONTEXTO ({it['Bench']}):</b> {it['Macro_Msg']} | 📉 <b>VIX:</b> {it['VIX']:.2f} ({it['VIX_St']})
        </div>
        """, unsafe_allow_html=True)
        
        k1, k2, k3, k4 = st.columns(4)
        sc = it['Score-score" style="color:#555;">{it['S_Tec']:.1f}</div><div class="alert-tag" style="background-color:{rsi_bg}; color:{rsi_txt};">{rsi_msg}</div></div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""<div class="metric-card" style="border:2px solid {clr};"><div class="score-label" style="color:{clr};">PUNTAJE</div><div class="big-score" style="color:{clr};">{sc:.0f}</div><div style="font-weight:bold; color:{clr};">{it['Verdict']}</div></div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="scorePROFIT")
        if it['CW'] > 0:
            fig.add_hline(y=it['CW'], line_dash="dot", line_color="orange", annotation_text="Call Wall")
            fig.add_hline(y=it['PW'], line_dash="dot", line_color="cyan", annotation_text="Put Wall")
            
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(t=30']
        clr = "#00C853" if sc >= 70 else "#D32F2F" if sc <= 40 else "#FBC02D"
        
        with k1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="score-label">TÉCNICO</div>
                <div class="big-score" style="color:#555;">{it['S_Tec']:.1f}</div>
                <div class="alert-label">ESTRUCTURA</div>
                <div class="big-score" style="color:#555;">{it['S_Opt']:.1f}</div>
                <div class="alert-tag" style="background-color:{sent_bg}; color:{sent_txt};">{it['Sentiment']}</div>
                <div style="font-size:0.75rem; color:#666; margin-top:4, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

else: st.info("👈 Comienza escaneando un lote.")
