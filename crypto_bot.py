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
# Tuplas: (Intervalo Kucoin, Etiqueta, Cantidad de velas)
TIMEFRAMES = [
    ("1week", "MENSUAL", 600), # Bajamos semanas para construir el mes
    ("1week", "SEMANAL", 200),
    ("1day", "DIARIO", 300)
]

ADX_TH = 20
ADX_LEN = 14

# --- LISTA DE MONEDAS (KuCoin) ---
COINS = sorted([
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'SHIB', 'DOT',
    'LINK', 'TRX', 'MATIC', 'LTC', 'BCH', 'NEAR', 'UNI', 'ICP', 'FIL', 'APT',
    'INJ', 'LDO', 'OP', 'ARB', 'TIA', 'SEI', 'SUI', 'RNDR', 'FET', 'WLD',
    'PEPE', 'BONK', 'WIF', 'FLOKI', 'ORDI', 'SATS', 'GALA', 'SAND', 'MANA',
    'AXS', 'AAVE', 'SNX', 'MKR', 'CRV', 'DYDX', 'JUP', 'PYTH', 'ENA', 'RUNE',
    'FTM', 'ATOM', 'ALGO', 'VET', 'EGLD', 'STX', 'IMX', 'KAS', 'TAO'
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

# --- MOTOR DE DATOS (KUCOIN API) ---
def get_kucoin_data(symbol, k_interval):
    url = "https://api.kucoin.com/api/v1/market/candles"
    target = f"{symbol}-USDT"
    limit = 1500 if k_interval == '1week' else 300
    
    params = {'symbol': target, 'type': k_interval, 'limit': limit}
    try:
        r = requests.get(url, params=params, timeout=5).json()
        if r['code'] == '200000':
            data = r['data']
            df = pd.DataFrame(data, columns=['Time','Open','Close','High','Low','Vol','Turn'])
            df = df.astype(float)
            df['Time'] = pd.to_datetime(df['Time'], unit='s')
            df = df.sort_values('Time', ascending=True).reset_index(drop=True)
            return df
    except: pass
    return pd.DataFrame()

# --- RESAMPLEO MENSUAL ---
def resample_to_monthly(df_weekly):
    if df_weekly.empty: return pd.DataFrame()
    df_weekly.set_index('Time', inplace=True)
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    try: df_monthly = df_weekly.resample('ME').agg(logic).dropna()
    except: df_monthly = df_weekly.resample('M').agg(logic).dropna()
    df_monthly = df_monthly.reset_index()
    return df_monthly

# --- CÁLCULOS MATEMÁTICOS ---
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
    p_dm_s = wilder(df['+DM'], period)
    n_dm_s = wilder(df['-DM'], period)
    p_di = 100 * (p_dm_s / tr_s)
    n_di = 100 * (n_dm_s / tr_s)
    dx = 100 * abs(p_di - n_di) / (p_di + n_di)
    return wilder(dx, period)

def calculate_atr(df, period=14):
    df = df.copy()
    df['H-L'] = df['High'] - df['Low']
    df['H-C'] = abs(df['High'] - df['Close'].shift(1))
    df['L-C'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
    return df['TR'].rolling(period).mean()

# --- BÚSQUEDA DE SEÑAL ---
def get_last_signal(df, adx_th):
    if len(df) < 20: return None
    
    df['ADX'] = calculate_adx(df)
    df['ATR'] = calculate_atr(df)
    df_ha = calculate_heikin_ashi(df)
    
    last_signal = None
    in_pos = False
    
    for i in range(1, len(df_ha)):
        c = df_ha['Color'].iloc[i]
        a = df['ADX'].iloc[i]
        d = df_ha['Time'].iloc[i]
        p = df_ha['Close'].iloc[i]
        atr = df['ATR'].iloc[i]
        
        sl = p - (2 * atr) if c == 1 else p + (2 * atr)
        tp = p + (3 * atr) if c == 1 else p - (3 * atr)
        
        if not in_pos and c == 1 and a > adx_th:
            in_pos = True
            last_signal = {"Tipo": "🟢 LONG", "Fecha": d, "Precio": p, "ADX": a, "Color": 1, "SL": sl, "TP": tp}
        elif in_pos and c == -1:
            in_pos = False
            last_signal = {"Tipo": "🔴 SHORT", "Fecha": d, "Precio": p, "ADX": a, "Color": -1, "SL": sl, "TP": tp}
            
    if not last_signal:
        curr = df_ha.iloc[-1]
        atr = df['ATR'].iloc[-1]
        p = curr['Close']
        c = curr['Color']
        sl = p - (2 * atr) if c == 1 else p + (2 * atr)
        tp = p + (3 * atr) if c == 1 else p - (3 * atr)
        t = "🟢 LONG" if c == 1 else "🔴 SHORT"
        last_signal = {"Tipo": t, "Fecha": curr['Time'], "Precio": p, "ADX": df['ADX'].iloc[-1], "Color": c, "SL": sl, "TP": tp}
        
    return last_signal

# --- EJECUCIÓN PRINCIPAL ---
def run_bot():
    print(f"--- SCAN: {datetime.now()} ---")
    send_message("⚡ **INICIANDO ESCANEO (KuCoin + Risk + Fix)**")
    
    market_map = {t: {} for t in COINS}
    all_signals_list = []

    # 1. ESCANEO
    for k_int, label, _ in TIMEFRAMES:
        for coin in COINS:
            try:
                df = get_kucoin_data(coin, k_int)
                if label == "MENSUAL": df = resample_to_monthly(df)
                if df.empty: continue

                sig = get_last_signal(df, ADX_TH)
                if sig:
                    # Mapeo claves
                    key_map = "1mo" if label == "MENSUAL" else "1wk" if label == "SEMANAL" else "1d"
                    market_map[coin][key_map] = sig['Color']
                    if label == 'DIARIO': market_map[coin]['Price'] = sig['Precio']
                    
                    all_signals_list.append({
                        "Ticker": coin, "TF": label, 
                        "Tipo": sig['Tipo'], "Precio": sig['Precio'], "ADX": sig['ADX'],
                        "SL": sig['SL'], "TP": sig['TP'],
                        "Fecha": sig['Fecha'], "Fecha_Str": sig['Fecha'].strftime('%d-%m-%Y')
                    })
                time.sleep(0.02)
            except: pass

    # --- REPORTE 1: EL MAPA (CORREGIDO PARA MOSTRAR TODO) ---
    full_bull, starting, pullback, full_bear = [], [], [], []
    
    for t, d in market_map.items():
        # --- FIX: Usamos .get() con valor 0 (Neutro) si falta algún dato ---
        m = d.get('1mo', 0)
        w = d.get('1wk', 0)
        day = d.get('1d', 0)
        
        # Si no tiene ningún dato, saltamos
        if m == 0 and w == 0 and day == 0: continue
        
        p = d.get('Price', 0)
        
        # Iconos visuales (Blanco si falta el dato)
        i_m = "🟢" if m==1 else "🔴" if m==-1 else "⚪"
        i_w = "🟢" if w==1 else "🔴" if w==-1 else "⚪"
        i_d = "🟢" if day==1 else "🔴" if day==-1 else "⚪"
        
        line = f"• {t}: ${p:,.4f} [{i_m} {i_w} {i_d}]"
        
        # Lógica de clasificación (más flexible)
        if m==1 and w==1 and day==1: full_bull.append(line)
        elif m<=0 and w==1 and day==1: starting.append(line)
        elif m==1 and w==1 and day==-1: pullback.append(line)
        elif m==-1 and w==-1 and day==-1: full_bear.append(line)

    map_msg = f"🦄 **MAPA KUCOIN** ({datetime.now().strftime('%d/%m')})\nLeyenda: [Mes Sem Dia]\n\n"
    if starting: map_msg += f"🌱 **NACIMIENTO**\n" + "\n".join(starting) + "\n\n"
    if full_bull: map_msg += f"🚀 **FULL BULL**\n" + "\n".join(full_bull) + "\n\n"
    if pullback: map_msg += f"⚠️ **CORRECCIÓN**\n" + "\n".join(pullback) + "\n\n"
    if full_bear: map_msg += f"🩸 **FULL BEAR**\n" + "\n".join(full_bear) + "\n\n"
    
    send_message(map_msg)
    time.sleep(2)

    # --- REPORTE 2: BITÁCORA ---
    if all_signals_list:
        all_signals_list.sort(key=lambda x: x['Fecha'], reverse=True)
        send_message(f"📋 **BITÁCORA CON RIESGO**\n(Ordenado por fecha):")
        
        for s in all_signals_list:
            icon = "🚨" if "SHORT" in s['Tipo'] else "🚀"
            msg = (
                f"{icon} **{s['Ticker']} ({s['TF']})**\n"
                f"**{s['Tipo']}**\n"
                f"Precio: ${s['Precio']}\n"
                f"ADX: {s['ADX']:.1f}\n"
                f"🛡 SL: ${s['SL']:.4f}\n"
                f"🎯 TP: ${s['TP']:.4f}\n"
                f"Fecha: {s['Fecha_Str']}"
            )
            send_message(msg)
            time.sleep(0.1)
    
    send_message("✅ Finalizado.")

if __name__ == "__main__":
    run_bot()
