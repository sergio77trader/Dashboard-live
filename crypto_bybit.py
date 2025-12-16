import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRYPTO") 

# --- CONFIGURACIÓN ESTRATEGIA ---
# Usamos códigos estándar internos: "M", "W", "D"
TIMEFRAMES = [
    ("M", "MENSUAL"),
    ("W", "SEMANAL"),
    ("D", "DIARIO")
]

ADX_TH = 20
ADX_LEN = 14

# --- LISTA BINANCE FUTURES (USDT) ---
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

# --- MOTOR DE DATOS HÍBRIDO (Anti-Bloqueo) ---
def fetch_data(symbol, tf_code):
    # Headers para parecer un navegador real y evitar bloqueos
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    # Mapeo de intervalos
    binance_map = {"M": "1M", "W": "1w", "D": "1d"}
    bybit_map = {"M": "M", "W": "W", "D": "D"}
    yahoo_map = {"M": "1mo", "W": "1wk", "D": "1d"}
    
    # 1. INTENTO BINANCE
    try:
        url = "https://fapi.binance.com/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': binance_map[tf_code], 'limit': 150}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Vol','x','x','x','x','x','x'])
            df['Time'] = pd.to_datetime(df['Time'], unit='ms')
            return df[['Time','Open','High','Low','Close','Vol']].astype(float)
    except: pass

    # 2. INTENTO BYBIT (Si Binance falla)
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {"category": "linear", "symbol": symbol, "interval": bybit_map[tf_code], "limit": 150}
        r = requests.get(url, params=params, headers=headers, timeout=5).json()
        if r['retCode'] == 0:
            df = pd.DataFrame(r['result']['list'], columns=['Time','Open','High','Low','Close','Vol','Turn'])
            df = df.astype(float).iloc[::-1].reset_index(drop=True) # Invertir orden
            df['Time'] = pd.to_datetime(df['Time'], unit='ms')
            return df[['Time','Open','High','Low','Close','Vol']]
    except: pass

    # 3. INTENTO YAHOO (Respaldo final - Garantía de datos)
    try:
        # Convertir ticker: BTCUSDT -> BTC-USD
        y_sym = symbol.replace("1000", "").replace("USDT", "-USD")
        # Fixes manuales
        if "PEPE" in symbol: y_sym = "PEPE24478-USD"
        if "BONK" in symbol: y_sym = "BONK-USD"
        if "SHIB" in symbol: y_sym = "SHIB-USD"
        if "WIF" in symbol: y_sym = "WIF-USD"
        
        df = yf.download(y_sym, interval=yahoo_map[tf_code], period="2y", progress=False, auto_adjust=True)
        if not df.empty:
            df = df.reset_index()
            # Normalizar nombres de columnas
            df.rename(columns={'Date': 'Time', 'Datetime': 'Time'}, inplace=True)
            return df[['Time','Open','High','Low','Close','Volume']]
    except: pass

    return pd.DataFrame() # Vacío si todo falla

# --- CÁLCULOS ---
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
    df['H-L'] = df['High'] - df['Low']
    df['H-C'] = abs(df['High'] - df['Close'].shift(1))
    df['L-C'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
    
    df['UpMove'] = df['High'] - df['High'].shift(1)
    df['DownMove'] = df['Low'].shift(1) - df['Low']
    df['+DM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['-DM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)
    
    def wilder(x, n): return x.ewm(alpha=1/n, adjust=False).mean()
    tr_s = wilder(df['TR'], period).replace(0, 1)
    p_di = 100 * (wilder(df['+DM'], period)/tr_s)
    n_di = 100 * (wilder(df['-DM'], period)/tr_s)
    dx = 100 * abs(p_di - n_di) / (p_di + n_di)
    return wilder(dx, period)

# --- ANÁLISIS ---
def get_signal(df, adx_th):
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    
    last_signal = None
    in_pos = False
    
    for i in range(1, len(df_ha)):
        c = df_ha['Color'].iloc[i]
        a = df['ADX'].iloc[i]
        d = df_ha['Time'].iloc[i]
        p = df_ha['Close'].iloc[i]
        
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

# --- MAIN LOOP ---
def run_bot():
    print(f"--- SCAN: {datetime.now()} ---")
    send_message("⚡ **ESCANEO CRIPTO INICIADO (Modo Híbrido)**")
    
    market_map = {t: {} for t in TICKERS}
    all_signals = []
    
    for tf_code, label in TIMEFRAMES:
        print(f"Analizando {label}...")
        for ticker in TICKERS:
            try:
                df = fetch_data(ticker, tf_code)
                if df.empty: continue
                
                sig = get_signal(df, ADX_TH)
                if sig:
                    market_map[ticker][tf_code] = sig['Color']
                    if tf_code == 'D': market_map[ticker]['Price'] = sig['Precio']
                    
                    all_signals.append({
                        "Ticker": ticker.replace("USDT",""),
                        "TF": label,
                        "Tipo": sig['Tipo'],
                        "Precio": sig['Precio'],
                        "ADX": sig['ADX'],
                        "Fecha": sig['Fecha'],
                        "Fecha_Str": sig['Fecha'].strftime('%d-%m-%Y')
                    })
                time.sleep(0.1)
            except: pass

    # --- REPORTE 1: MAPA ---
    full_bull, starting, pullback, full_bear = [], [], [], []
    for t, d in market_map.items():
        if not all(k in d for k in ['M','W','D']): continue
        m, w, day = d['M'], d['W'], d['D']
        p = d.get('Price', 0)
        line = f"• {t.replace('USDT','')}: ${p:,.4f}"
        
        if m==1 and w==1 and day==1: full_bull.append(line)
        elif m<=0 and w==1 and day==1: starting.append(line)
        elif m==1 and w==1 and day==-1: pullback.append(line)
        elif m==-1 and w==-1 and day==-1: full_bear.append(line)

    msg = f"₿ **MAPA CRIPTO** ({datetime.now().strftime('%d/%m')})\nLeyenda: [Mes Sem Dia]\n\n"
    if starting: msg += f"🌱 **NACIMIENTO**\n" + "\n".join(starting) + "\n\n"
    if full_bull: msg += f"🚀 **FULL BULL**\n" + "\n".join(full_bull) + "\n\n"
    if pullback: msg += f"⚠️ **CORRECCIÓN**\n" + "\n".join(pullback) + "\n\n"
    if full_bear: msg += f"🩸 **FULL BEAR**\n" + "\n".join(full_bear[:15]) + "\n..."
    
    send_message(msg)
    time.sleep(2)

    # --- REPORTE 2: BITÁCORA ---
    if all_signals:
        all_signals.sort(key=lambda x: x['Fecha'], reverse=True)
        send_message(f"📋 **BITÁCORA ORDENADA**")
        for s in all_signals:
            icon = "🚨" if "SHORT" in s['Tipo'] else "🚀"
            txt = f"{icon} **{s['Ticker']} ({s['TF']})**\n**{s['Tipo']}**\nPrecio: ${s['Precio']}\nADX: {s['ADX']:.1f}\nFecha: {s['Fecha_Str']}"
            send_message(txt)
            time.sleep(0.2)
            
    send_message("✅ Finalizado.")

if __name__ == "__main__":
    run_bot()
