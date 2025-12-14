import os
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- CREDENCIALES CRIPTO ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRYPTO") 

# --- CONFIGURACIÓN ---
TIMEFRAMES = [("1M", "MENSUAL", 100), ("1w", "SEMANAL", 250), ("1d", "DIARIO", 365)]
ADX_TH = 20
ADX_LEN = 14

# --- BASE DE DATOS CRIPTO ---
TICKERS = sorted([
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'SHIBUSDT', 'DOTUSDT',
    'LINKUSDT', 'TRXUSDT', 'MATICUSDT', 'LTCUSDT', 'BCHUSDT', 'NEARUSDT', 'UNIUSDT', 'ICPUSDT', 'FILUSDT', 'APTUSDT',
    'INJUSDT', 'LDOUSDT', 'OPUSDT', 'ARBUSDT', 'TIAUSDT', 'SEIUSDT', 'SUIUSDT', 'RNDRUSDT', 'FETUSDT', 'WLDUSDT',
    'PEPEUSDT', 'BONKUSDT', 'WIFUSDT', 'FLOKIUSDT', 'ORDIUSDT', 'SATSUSDT', '1000PEPEUSDT', '1000SHIBUSDT', '1000BONKUSDT',
    'GALAUSDT', 'SANDUSDT', 'MANAUSDT', 'AXSUSDT', 'AAVEUSDT', 'SNXUSDT', 'MKRUSDT', 'CRVUSDT', 'DYDXUSDT', 'JUPUSDT',
    'PYTHUSDT', 'ENAUSDT', 'RUNEUSDT', 'FTMUSDT', 'ATOMUSDT', 'ALGOUSDT', 'VETUSDT', 'EGLDUSDT', 'STXUSDT', 'IMXUSDT'
])

def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        if len(msg) > 4000:
            parts = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for p in parts:
                requests.post(url, data={"chat_id": CHAT_ID, "text": p, "parse_mode": "Markdown"})
                time.sleep(1)
        else:
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def get_binance_data(symbol, interval, limit):
    url = "https://fapi.binance.com/fapi/v1/klines"
    try:
        r = requests.get(url, params={'symbol': symbol, 'interval': interval, 'limit': limit}, timeout=10)
        df = pd.DataFrame(r.json(), columns=['Time','Open','High','Low','Close','Vol','x','x','x','x','x','x'])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        return df[['Time','Open','High','Low','Close']].astype({'Open':float,'High':float,'Low':float,'Close':float})
    except: return pd.DataFrame()

# (Mismas funciones matemáticas que el de acciones, repetidas para que sea autónomo)
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)): ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def calculate_adx(df, period=14):
    df = df.copy()
    df['TR'] = np.maximum(df['High']-df['Low'], np.maximum(abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())))
    df['+DM'] = np.where((df['High']-df['High'].shift()) > (df['Low'].shift()-df['Low']), np.maximum(df['High']-df['High'].shift(),0), 0)
    df['-DM'] = np.where((df['Low'].shift()-df['Low']) > (df['High']-df['High'].shift()), np.maximum(df['Low'].shift()-df['Low'],0), 0)
    
    def wilder(x, n): return x.ewm(alpha=1/n, adjust=False).mean()
    tr_s = wilder(df['TR'], period).replace(0,1)
    dx = 100 * abs((100*wilder(df['+DM'],period)/tr_s) - (100*wilder(df['-DM'],period)/tr_s)) / ((100*wilder(df['+DM'],period)/tr_s) + (100*wilder(df['-DM'],period)/tr_s))
    return wilder(dx, period)

def get_last_signal(df, adx_th):
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    last_signal = None
    in_pos = False
    
    for i in range(1, len(df_ha)):
        c, a, d, p = df_ha['Color'].iloc[i], df['ADX'].iloc[i], df_ha['Time'].iloc[i], df_ha['Close'].iloc[i]
        if not in_pos and c == 1 and a > adx_th:
            in_pos = True
            last_signal = {"Tipo": "🟢 LONG", "Fecha": d, "Precio": p, "ADX": a, "Color": 1}
        elif in_pos and c == -1:
            in_pos = False
            last_signal = {"Tipo": "🔴 SHORT", "Fecha": d, "Precio": p, "ADX": a, "Color": -1}
            
    if not last_signal:
        curr = df_ha.iloc[-1]
        t = "🟢 LONG" if curr['Color'] == 1 else "🔴 SHORT"
        last_signal = {"Tipo": t, "Fecha": curr['Time'], "Precio": curr['Close'], "ADX": df['ADX'].iloc[-1], "Color": curr['Color']}
    return last_signal

def run_bot():
    print(f"--- CRIPTO START: {datetime.now()} ---")
    market_map = {t: {} for t in TICKERS}
    all_signals = []
    
    for interval, label, limit in TIMEFRAMES:
        for t in TICKERS:
            try:
                df = get_binance_data(t, interval, limit)
                if df.empty: continue
                sig = get_last_signal(df, ADX_TH)
                if sig:
                    market_map[t][interval] = sig['Color']
                    if interval == '1d': market_map[t]['Price'] = sig['Precio']
                    all_signals.append({
                        "Ticker": t.replace("USDT",""), "TF": label, "Data": sig, "SortDate": sig['Fecha']
                    })
                time.sleep(0.05)
            except: pass

    # Reporte 1
    full_bull, starting, pullback, full_bear = [], [], [], []
    for t, d in market_map.items():
        if not all(k in d for k in ['1M','1w','1d']): continue
        m, w, day = d['1M'], d['1w'], d['1d']
        line = f"• {t.replace('USDT','')}: ${d.get('Price',0):.4f}"
        if m==1 and w==1 and day==1: full_bull.append(line)
        elif m<=0 and w==1 and day==1: starting.append(line)
        elif m==1 and w==1 and day==-1: pullback.append(line)
        elif m==-1 and w==-1 and day==-1: full_bear.append(line)
        
    msg = f"₿ **MAPA CRIPTO** ({datetime.now().strftime('%d/%m')})\n\n"
    if starting: msg += f"🌱 **NACIMIENTO**\n" + "\n".join(starting) + "\n\n"
    if full_bull: msg += f"🚀 **FULL BULL**\n" + "\n".join(full_bull) + "\n\n"
    if pullback: msg += f"⚠️ **CORRECCIÓN**\n" + "\n".join(pullback) + "\n\n"
    if full_bear: msg += f"🩸 **FULL BEAR**\n" + "\n".join(full_bear) + "\n\n"
    send_message(msg)
    time.sleep(2)

    # Reporte 2
    if all_signals:
        all_signals.sort(key=lambda x: x['SortDate'], reverse=True)
        send_message("📋 **BITÁCORA CRIPTO (Ordenada)**")
        for s in all_signals:
            d = s['Data']
            icon = "🚨" if "SHORT" in d['Tipo'] else "🚀"
            txt = f"{icon} **{s['Ticker']} ({s['TF']})**\n**{d['Tipo']}**\nPrecio: ${d['Precio']}\nADX: {d['ADX']:.1f}\nFecha: {d['Fecha'].strftime('%d-%m-%Y')}"
            send_message(txt)
            time.sleep(0.3)
    
    send_message("✅ Fin reporte Cripto.")

if __name__ == "__main__":
    run_bot()
