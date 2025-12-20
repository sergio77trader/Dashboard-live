import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- CONFIGURACIÓN ---
TIMEFRAMES = [
    ("1d", "DIARIO", "2y"),
    ("1wk", "SEMANAL", "10y"),
    ("1mo", "MENSUAL", "max")
]
ADX_TH = 20

# --- BASE DE DATOS ---
TICKERS = sorted(['GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'AAPL', 'MSFT', 'NVDA', 'META', 'TSLA', 'MELI', 'VIST', 'GLOB', 'SPY', 'QQQ']) # Agrega los que faltan

def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

# --- CÁLCULOS TÉCNICOS ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def calculate_adx(df, period=14):
    df = df.copy()
    df['H-L'], df['H-C'], df['L-C'] = df['High']-df['Low'], abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
    df['UpMove'], df['DownMove'] = df['High']-df['High'].shift(1), df['Low'].shift(1)-df['Low']
    df['+DM'] = np.where((df['UpMove']>df['DownMove']) & (df['UpMove']>0), df['UpMove'], 0)
    df['-DM'] = np.where((df['DownMove']>df['UpMove']) & (df['DownMove']>0), df['DownMove'], 0)
    def wilder(x, p): return x.ewm(alpha=1/p, adjust=False).mean()
    tr_s = wilder(df['TR'], period).replace(0, 1)
    p_di, n_di = 100*(wilder(df['+DM'], period)/tr_s), 100*(wilder(df['-DM'], period)/tr_s)
    return wilder(100 * abs(p_di - n_di) / (p_di + n_di), period)

def get_last_signal(df, adx_th):
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    last_sig, in_pos = None, False
    for i in range(1, len(df_ha)):
        c, a, d, p = df_ha['Color'].iloc[i], df['ADX'].iloc[i], df_ha.index[i], df_ha['Close'].iloc[i]
        if not in_pos and c == 1 and a > adx_th:
            in_pos, last_sig = True, {"T": "LONG", "F": d, "P": p, "A": a, "C": 1}
        elif in_pos and c == -1:
            in_pos, last_sig = False, {"T": "SHORT", "F": d, "P": p, "A": a, "C": -1}
    if not last_sig:
        curr = df_ha.iloc[-1]
        last_sig = {"T": "LONG" if curr['Color']==1 else "SHORT", "F": curr.name, "P": curr['Close'], "A": df['ADX'].iloc[-1], "C": int(curr['Color'])}
    return last_sig

# --- MOTOR PRINCIPAL ---
def run_bot():
    print(f"--- START SCAN: {datetime.now()} ---")
    master_data = {}
    ahora = datetime.now()

    for interval, label, period in TIMEFRAMES:
        try:
            data = yf.download(TICKERS, interval=interval, period=period, group_by='ticker', progress=False, auto_adjust=True)
            for ticker in TICKERS:
                if ticker not in master_data: 
                    master_data[ticker] = {'DIARIO':None,'SEMANAL':None,'MENSUAL':None,'Price':0,'LastDate':datetime(2000,1,1)}
                
                df = data[ticker].dropna() if len(TICKERS)>1 else data.dropna()
                if df.empty: continue
                
                sig = get_last_signal(df, ADX_TH)
                if sig:
                    master_data[ticker][label] = sig
                    if label == 'DIARIO': master_data[ticker]['Price'] = df['Close'].iloc[-1]
                    if sig['F'] > master_data[ticker]['LastDate']: master_data[ticker]['LastDate'] = sig['F']
        except Exception as e: print(f"Error en {label}: {e}")

    # Ordenar por actividad reciente
    sorted_tickers = sorted([i for i in master_data.items() if i[1]['DIARIO']], key=lambda x: x[1]['LastDate'], reverse=True)
    
    report_msg = "📋 **REPORTE TÉCNICO DE ACTIVOS**\n\n"
    
    for ticker, info in sorted_tickers:
        ficha = f"**{ticker}** | ${info['Price']:,.2f}\n"
        ficha += "━━━━━━━━━━━━━━━━━━\n"
        
        for tf_key, tf_label in [('DIARIO','D'), ('SEMANAL','S'), ('MENSUAL','M')]:
            s = info[tf_key]
            if s:
                ball = "🟢" if s['C'] == 1 else "🔴"
                # Lógica de resaltado: Si la señal tiene menos de 48hs de antigüedad
                es_reciente = (ahora - s['F'].replace(tzinfo=None)).days <= 2
                
                linea = f"{ball} **{tf_label}** {s['T']} | ${s['P']:,.2f} | ADX:{s['A']:.1f} | {s['F'].strftime('%d/%m/%Y')}"
                
                if es_reciente:
                    ficha += f"🆕 **{linea}**\n" # Negrita total y marcador NEW
                else:
                    ficha += f"{linea}\n"
            else:
                ficha += f"⚪ **{tf_label}** | Sin Datos\n"
        
        ficha += "━━━━━━━━━━━━━━━━━━\n\n"
        report_msg += ficha
        
        if len(report_msg) > 3500:
            send_message(report_msg)
            report_msg = ""
            time.sleep(1)

    if report_msg: send_message(report_msg)

if __name__ == "__main__":
    run_bot()
