import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- CONFIGURACIÓN ---
TIMEFRAMES = [
    ("1mo", "MENSUAL", "max"), 
    ("1wk", "SEMANAL", "10y"), 
    ("1d", "DIARIO", "5y")
]

# --- BASE DE DATOS COMPLETA ---
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

def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # Dividir mensajes largos (Telegram limita a 4096 chars)
        if len(msg) > 4000:
            parts = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for p in parts:
                requests.post(url, data={"chat_id": CHAT_ID, "text": p, "parse_mode": "Markdown"})
                time.sleep(1)
        else:
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

# --- CÁLCULOS MATEMÁTICOS ---
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

# --- MOTOR DE SIMULACIÓN ---
def analyze_ticker(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        
        position = "FLAT"
        
        # Bucle de Simulación
        for i in range(1, len(df)):
            c_ha = df['HA_Color'].iloc[i]
            c_hist = df['Hist'].iloc[i]
            p_hist = df['Hist'].iloc[i-1]
            
            # Salidas (Stop Momentum)
            if position == "LONG" and c_hist < p_hist: position = "FLAT"
            elif position == "SHORT" and c_hist > p_hist: position = "FLAT"

            # Entradas (Smart Entry)
            if position == "FLAT":
                # Long: HA Verde + Hist < 0 + Hist Subiendo
                if c_ha == 1 and (c_hist < 0) and (c_hist > p_hist): position = "LONG"
                # Short: HA Rojo + Hist > 0 + Hist Bajando
                elif c_ha == -1 and (c_hist > 0) and (c_hist < p_hist): position = "SHORT"
        
        # Info Final
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Datos para Neutro (HA y MACD Status)
        ha_icon = "🟢" if last_row['HA_Color'] == 1 else "🔴"
        macd_icon = "🟢" if last_row['Hist'] > prev_row['Hist'] else "🔴"
        price = last_row['Close']
        
        return {
            "Ticker": ticker,
            "Estado": position,
            "Precio": price,
            "Detalle_Neutro": f"HA {ha_icon} | MACD {macd_icon}"
        }

    except: return None

def run_bot():
    print(f"--- START: {datetime.now()} ---")
    send_message("⚡ **INICIANDO ESCANEO MAESTRO...**")
    
    # Almacén de resultados
    # Estructura: {'LONG': [], 'SHORT': [], 'NEUTRO': []} por cada TF
    report_data = {
        'MENSUAL': {'LONG': [], 'SHORT': [], 'NEUTRO': []},
        'SEMANAL': {'LONG': [], 'SHORT': [], 'NEUTRO': []},
        'DIARIO':  {'LONG': [], 'SHORT': [], 'NEUTRO': []}
    }

    # 1. ESCANEO
    for interval, label, period in TIMEFRAMES:
        print(f"Analizando {label}...")
        
        # Descarga masiva para caché (opcional, aquí iteramos para robustez)
        # Usamos iteración simple para asegurar cálculo
        for ticker in TICKERS:
            res = analyze_ticker(ticker, interval, period)
            if res:
                state = res['Estado']
                line = f"• **{ticker}:** ${res['Precio']:.2f}"
                
                if state == "LONG":
                    report_data[label]['LONG'].append(line)
                elif state == "SHORT":
                    report_data[label]['SHORT'].append(line)
                else:
                    # En neutro agregamos el detalle visual
                    line += f" ({res['Detalle_Neutro']})"
                    report_data[label]['NEUTRO'].append(line)
            
            # Pequeña pausa para no saturar CPU en local o server
            # time.sleep(0.01)

    # 2. GENERAR MENSAJE
    msg = f"📊 **REPORTE SYSTEMATRADER** ({datetime.now().strftime('%d/%m')})\n\n"
    
    for label in ["MENSUAL", "SEMANAL", "DIARIO"]:
        data = report_data[label]
        
        msg += f"📅 **{label}**\n"
        
        if data['LONG']:
            msg += f"🟢 **LONG ({len(data['LONG'])}):**\n" + "\n".join(data['LONG']) + "\n"
        
        if data['SHORT']:
            msg += f"🔴 **SHORT ({len(data['SHORT'])}):**\n" + "\n".join(data['SHORT']) + "\n"
            
        # Opcional: Mostrar Neutros "Calientes" (ej: HA Verde y MACD Verde)
        # Filtramos los neutros que tienen doble verde o doble rojo para no llenar de basura
        hot_neutrals = [x for x in data['NEUTRO'] if "HA 🟢 | MACD 🟢" in x]
        cold_neutrals = [x for x in data['NEUTRO'] if "HA 🔴 | MACD 🔴" in x]
        
        if hot_neutrals:
            msg += f"👀 **ATENTOS (Neutro Alcista):**\n" + "\n".join(hot_neutrals) + "\n"
            
        # Separador entre TFs
        msg += "\n━━━━━━━━━━━━━━\n\n"

    send_message(msg)
    print("Reporte enviado.")

if __name__ == "__main__":
    run_bot()
