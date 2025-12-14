import os
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# Puedes usar el mismo chat ID o uno específico para cripto si creaste el secreto
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") 

# --- CONFIGURACIÓN ---
# Binance API Intervals: 1M (Mes), 1w (Semana), 1d (Día)
TIMEFRAMES = [
    ("1M", "MENSUAL", 100),  # Limit: Cantidad de velas hacia atrás
    ("1w", "SEMANAL", 200),
    ("1d", "DIARIO", 365)
]

ADX_TH = 20
ADX_LEN = 14

# --- BASE DE DATOS (BINANCE FUTURES USDT) ---
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
        # Dividir mensajes largos
        if len(msg) > 4000:
            parts = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for p in parts:
                requests.post(url, data={"chat_id": CHAT_ID, "text": p, "parse_mode": "Markdown"})
                time.sleep(1)
        else:
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

# --- MOTOR DE DATOS (BINANCE API) ---
def get_binance_data(symbol, interval, limit):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        # Estructura: [Time, Open, High, Low, Close, ...]
        df = pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Vol','x','x','x','x','x','x'])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        df = df[['Time','Open','High','Low','Close']].astype({'Open':float,'High':float,'Low':float,'Close':float})
        return df
    except: return pd.DataFrame()

# --- CÁLCULOS MATEMÁTICOS ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    
    # 1 = Verde (Long), -1 = Rojo (Short)
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
    
    def wilder(x, period): return x.ewm(alpha=1/period, adjust=False).mean()

    tr_s = wilder(df['TR'], period).replace(0, 1)
    p_dm_s = wilder(df['+DM'], period)
    n_dm_s = wilder(df['-DM'], period)
    
    p_di = 100 * (p_dm_s / tr_s)
    n_di = 100 * (n_dm_s / tr_s)
    dx = 100 * abs(p_di - n_di) / (p_di + n_di)
    return wilder(dx, period)

# --- MOTOR DE BÚSQUEDA ---
def get_last_signal(df, adx_th):
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    
    last_signal = None
    in_position = False
    
    for i in range(1, len(df_ha)):
        color = df_ha['Color'].iloc[i]
        adx = df['ADX'].iloc[i]
        date = df_ha['Time'].iloc[i]
        price = df_ha['Close'].iloc[i]
        
        # LONG (Compra)
        if not in_position and color == 1 and adx > adx_th:
            in_position = True
            last_signal = {"Tipo": "🟢 LONG", "Fecha": date, "Precio": price, "ADX": adx, "Color": 1}
        # SHORT (Venta)
        elif in_position and color == -1:
            in_position = False
            last_signal = {"Tipo": "🔴 SHORT", "Fecha": date, "Precio": price, "ADX": adx, "Color": -1}
            
    # Si no hubo cruce, estado actual
    if not last_signal:
        curr = df_ha.iloc[-1]
        t = "🟢 LONG" if curr['Color'] == 1 else "🔴 SHORT"
        last_signal = {"Tipo": t, "Fecha": curr['Time'], "Precio": curr['Close'], "ADX": df['ADX'].iloc[-1], "Color": curr['Color']}
        
    return last_signal

def run_bot():
    print(f"--- START CRYPTO SCAN: {datetime.now()} ---")
    
    market_summary = {t: {} for t in TICKERS}
    all_signals_list = []

    # 1. ESCANEO
    for interval, label, limit in TIMEFRAMES:
        print(f"Procesando {label}...")
        for ticker in TICKERS:
            try:
                # Usar Binance API
                df = get_binance_data(ticker, interval, limit)
                if df.empty: continue

                sig = get_last_signal(df, ADX_TH)
                
                if sig:
                    # Guardar para Mapa
                    market_summary[ticker][interval] = sig['Color']
                    if interval == '1d': market_summary[ticker]['Price'] = sig['Precio']
                    
                    # Guardar para Detalle
                    all_signals_list.append({
                        "Ticker": ticker.replace("USDT", ""),
                        "TF": label,
                        "Tipo": sig['Tipo'],
                        "Precio": sig['Precio'],
                        "ADX": sig['ADX'],
                        "Fecha": sig['Fecha'],
                        "Fecha_Str": sig['Fecha'].strftime('%d-%m-%Y')
                    })
                time.sleep(0.05) # Rate limit suave
            except: pass

    # --- REPORTE 1: MAPA CRIPTO ---
    full_bull, starting_bull, pullback, full_bear = [], [], [], []
    icon_map = {1: "🟢", -1: "🔴", 0: "⚪"}
    
    for t, d in market_summary.items():
        if '1M' not in d or '1w' not in d or '1d' not in d: continue # Claves de Binance (1M, 1w, 1d)
        
        m, w, day = d['1M'], d['1w'], d['1d']
        p = d.get('Price', 0)
        clean_t = t.replace("USDT", "")
        
        line = f"• {clean_t}: ${p:,.4f}"
        
        if m==1 and w==1 and day==1: full_bull.append(line)
        elif m<=0 and w==1 and day==1: starting_bull.append(line)
        elif m==1 and w==1 and day==-1: pullback.append(line)
        elif m==-1 and w==-1 and day==-1: full_bear.append(line)

    map_msg = f"₿ **MAPA CRIPTO PERPETUOS** ({datetime.now().strftime('%d/%m')})\nLeyenda: [Mes Sem Dia]\n\n"
    if starting_bull: map_msg += f"🌱 **NACIMIENTO TENDENCIA**\n" + "\n".join(starting_bull) + "\n\n"
    if full_bull: map_msg += f"🚀 **FULL BULL**\n" + "\n".join(full_bull) + "\n\n"
    if pullback: map_msg += f"⚠️ **CORRECCIÓN**\n" + "\n".join(pullback) + "\n\n"
    if full_bear: map_msg += f"🩸 **FULL BEAR**\n" + "\n".join(full_bear) + "\n\n"
    
    send_message(map_msg)
    time.sleep(2)

    # --- REPORTE 2: DETALLE ORDENADO POR FECHA ---
    if all_signals_list:
        # Ordenar: Más reciente primero
        all_signals_list.sort(key=lambda x: x['Fecha'], reverse=True)
        
        send_message(f"📋 **BITÁCORA CRIPTO**\nMostrando las últimas señales de {len(TICKERS)} pares:\n(Ordenadas por fecha reciente)")
        
        # Filtro de cantidad opcional (ej: Top 50 más recientes para no saturar)
        for s in all_signals_list[:50]: 
            icon = "🚨" if "SHORT" in s['Tipo'] else "🚀"
            msg = (
                f"{icon} **{s['Ticker']} ({s['TF']})**\n"
                f"**{s['Tipo']}**\n"
                f"Precio: ${s['Precio']}\n"
                f"ADX: {s['ADX']:.1f}\n"
                f"Fecha Señal: {s['Fecha_Str']}"
            )
            send_message(msg)
            time.sleep(0.2)

if __name__ == "__main__":
    run_bot()
