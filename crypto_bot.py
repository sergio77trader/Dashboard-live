import os
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRYPTO")

# --- CONFIGURACIÓN ---
TIMEFRAMES = [
    ("1w", "MENSUAL*", 120),   # mensual simulado
    ("1w", "SEMANAL", 60),
    ("1d", "DIARIO", 120)
]

ADX_TH = 20

# --- TICKERS ---
TICKERS = sorted([
    'BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT','AVAXUSDT','DOGEUSDT',
    'SHIBUSDT','DOTUSDT','LINKUSDT','TRXUSDT','MATICUSDT','LTCUSDT','BCHUSDT','NEARUSDT',
    'UNIUSDT','ICPUSDT','FILUSDT','APTUSDT','INJUSDT','LDOUSDT','OPUSDT','ARBUSDT',
    'TIAUSDT','SEIUSDT','SUIUSDT','RNDRUSDT','FETUSDT','WLDUSDT'
])

# --- TELEGRAM ---
def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        time.sleep(0.5)
    except:
        pass

# --- BINANCE SPOT ---
def get_binance_data(symbol, interval, limit):
    url = "https://api.binance.com/api/v3/klines"
    try:
        r = requests.get(url, params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }, timeout=10)

        if r.status_code != 200:
            return pd.DataFrame()

        data = r.json()
        if not isinstance(data, list) or len(data) < 50:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            'Time','Open','High','Low','Close','Vol','x','x','x','x','x','x'
        ])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        return df[['Time','Open','High','Low','Close']].astype(float)

    except:
        return pd.DataFrame()

# --- HEIKIN ASHI ---
def calculate_heikin_ashi(df):
    ha = df.copy()
    ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha['HA_Close'].iloc[i-1]) / 2)
    ha['HA_Open'] = ha_open
    ha['Color'] = np.where(ha['HA_Close'] > ha['HA_Open'], 1, -1)
    return ha

# --- ADX ---
def calculate_adx(df, period=14):
    df = df.copy()
    df['TR'] = np.maximum(
        df['High'] - df['Low'],
        np.maximum(abs(df['High'] - df['Close'].shift()),
                   abs(df['Low'] - df['Close'].shift()))
    )
    df['+DM'] = np.where(
        (df['High'] - df['High'].shift()) > (df['Low'].shift() - df['Low']),
        np.maximum(df['High'] - df['High'].shift(), 0), 0
    )
    df['-DM'] = np.where(
        (df['Low'].shift() - df['Low']) > (df['High'] - df['High'].shift()),
        np.maximum(df['Low'].shift() - df['Low'], 0), 0
    )

    def wilder(x, n): return x.ewm(alpha=1/n, adjust=False).mean()

    tr = wilder(df['TR'], period).replace(0, 1)
    plus = 100 * wilder(df['+DM'], period) / tr
    minus = 100 * wilder(df['-DM'], period) / tr
    dx = 100 * abs(plus - minus) / (plus + minus)
    return wilder(dx, period)

# --- SEÑAL ---
def get_last_signal(df):
    df['ADX'] = calculate_adx(df)
    ha = calculate_heikin_ashi(df)
    curr = ha.iloc[-1]

    if curr['Color'] == 1 and df['ADX'].iloc[-1] > ADX_TH:
        return 1, curr['Close']
    elif curr['Color'] == -1:
        return -1, curr['Close']
    return 0, curr['Close']

# --- MAIN ---
def run_bot():
    market = {t: {} for t in TICKERS}

    for interval, label, limit in TIMEFRAMES:
        for t in TICKERS:
            df = get_binance_data(t, interval, limit)
            if df.empty:
                continue
            color, price = get_last_signal(df)
            market[t][label] = color
            if label == "DIARIO":
                market[t]["Price"] = price
            time.sleep(0.2)

    bull, start, pull, bear = [], [], [], []

    for t, d in market.items():
        if not all(k in d for k in ["MENSUAL*", "SEMANAL", "DIARIO"]):
            continue
        m, w, d1 = d["MENSUAL*"], d["SEMANAL"], d["DIARIO"]
        line = f"• {t.replace('USDT','')}: ${d.get('Price',0):.2f}"

        if m==1 and w==1 and d1==1: bull.append(line)
        elif m<=0 and w==1 and d1==1: start.append(line)
        elif m==1 and w==1 and d1==-1: pull.append(line)
        elif m==-1 and w==-1 and d1==-1: bear.append(line)

    msg = f"₿ MAPA CRIPTO ({datetime.now().strftime('%d/%m')})\n\n"
    if start: msg += "🌱 NACIMIENTO\n" + "\n".join(start) + "\n\n"
    if bull: msg += "🚀 FULL BULL\n" + "\n".join(bull) + "\n\n"
    if pull: msg += "⚠️ CORRECCIÓN\n" + "\n".join(pull) + "\n\n"
    if bear: msg += "🩸 FULL BEAR\n" + "\n".join(bear) + "\n\n"

    if not any([bull, start, pull, bear]):
        msg += "ℹ️ Sin activos con estructura completa"

    send_message(msg)
    send_message("✅ Fin reporte Cripto")

if __name__ == "__main__":
    run_bot()
