import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os  # <--- FALTABA ESTO
from datetime import datetime

# --- 1. CREDENCIALES (MODO GITHUB ACTIONS) ---
# Esto permite que el script lea los secretos que configuraste en el archivo YAML
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- 2. BASE DE DATOS MAESTRA ---
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

# --- 3. ENVÍO ---
def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: 
        print("Error de Credenciales")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    if len(message) < 4000:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    else:
        parts = message.split('\n\n')
        buffer = ""
        for part in parts:
            if len(buffer) + len(part) + 4 > 4000:
                requests.post(url, data={"chat_id": CHAT_ID, "text": buffer, "parse_mode": "Markdown"})
                time.sleep(1)
                buffer = part + "\n\n"
            else:
                buffer += part + "\n\n"
        if buffer:
            requests.post(url, data={"chat_id": CHAT_ID, "text": buffer, "parse_mode": "Markdown"})

# --- 4. INDICADORES ---
def calculate_strategy(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha_close.iloc[i-1]) / 2)
    
    df['Hist'] = hist
    df['HA_Color'] = np.where(ha_close > ha_open, 1, -1)
    return df

def get_last_signal(df):
    if df.empty: return "N/A", 0, None
    position = "FLAT"
    entry_price = 0.0
    entry_date = df.index[0]
    
    for i in range(1, len(df)):
        c_ha = df['HA_Color'].iloc[i]
        c_hist = df['Hist'].iloc[i]
        p_hist = df['Hist'].iloc[i-1]
        date = df.index[i]
        price = df['Close'].iloc[i]
        
        if position == "LONG" and c_hist < p_hist: position = "FLAT"
        if position == "SHORT" and c_hist > p_hist: position = "FLAT"
        
        if position == "FLAT":
            if c_ha == 1 and c_hist < 0 and c_hist > p_hist:
                position = "LONG"
                entry_date = date
                entry_price = price
            elif c_ha == -1 and c_hist > 0 and c_hist < p_hist:
                position = "SHORT"
                entry_date = date
                entry_price = price
                
    if position == "LONG":
        return "🟢 LONG", entry_price, entry_date
    elif position == "SHORT":
        return "🔴 SHORT", entry_price, entry_date
    else:
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        ha_icon = "🟢" if last_row['HA_Color'] == 1 else "🔴"
        macd_icon = "🟢" if last_row['Hist'] > prev_row['Hist'] else "🔴"
        return f"⚪ NEUTRO (HA {ha_icon} | MACD {macd_icon})", last_row['Close'], last_row.name

# --- 5. MOTOR PRINCIPAL ---
def run_analysis():
    print("⏳ Descargando datos masivos...")
    master_data = {}
    configs = [('D', '1d', '2y'), ('S', '1wk', '5y'), ('M', '1mo', 'max')]
    
    for label, interval, period in configs:
        print(f"-> Procesando {label}...")
        try:
            data = yf.download(TICKERS, interval=interval, period=period, group_by='ticker', progress=False, auto_adjust=True, threads=True)
            for t in TICKERS:
                if t not in master_data: master_data[t] = {}
                try:
                    if len(TICKERS) > 1: df = data[t].dropna()
                    else: df = data.dropna()
                    
                    if df.empty: continue
                    if label == 'D': master_data[t]['Current_Price'] = df['Close'].iloc[-1]
                    df = calculate_strategy(df)
                    sig, price, date = get_last_signal(df)
                    master_data[t][label] = {'Signal': sig, 'Entry_Price': price, 'Date': date}
                except: pass
        except Exception as e: print(e)

    # --- 6. PROCESAMIENTO ---
    print("⚙️ Generando reporte...")
    report_list = []
    
    for t, info in master_data.items():
        if 'Current_Price' not in info or not all(k in info for k in ['D','S','M']): continue
        
        dates = [info['D']['Date'], info['S']['Date'], info['M']['Date']]
        valid_dates = [d for d in dates if d is not None]
        if not valid_dates: continue
        
        max_date = max(valid_dates)
        
        lines = []
        lines.append(f"🔹 **{t}** - ${info['Current_Price']:.2f}")
        
        for tf in ['D', 'S', 'M']:
            data = info[tf]
            sig = data['Signal']
            price = data['Entry_Price']
            date_obj = data['Date']
            date_str = date_obj.strftime('%d/%m/%y') if date_obj else "-"
            
            is_newest = (date_obj == max_date)
            # FILTRO: Solo marcamos NEW si NO es neutro
            is_active_signal = "LONG" in sig or "SHORT" in sig
            
            should_highlight = is_newest and is_active_signal
            
            prefix = "🆕 " if should_highlight else ""
            fmt = "**" if should_highlight else ""
            
            line_str = f"{prefix}{tf} {sig} - ${price:.2f} - {date_str}"
            lines.append(f"{fmt}{line_str}{fmt}")
            
        report_list.append({'sort_date': max_date, 'text': "\n".join(lines)})
    
    report_list.sort(key=lambda x: x['sort_date'], reverse=True)
    
    final_msg = f"🦅 **REPORTE SYSTEMATRADER**\n📅 {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    body = "\n\n".join([item['text'] for item in report_list])
    send_telegram_msg(final_msg + body)
    print("✅ Reporte enviado.")

if __name__ == "__main__":
    run_analysis()
