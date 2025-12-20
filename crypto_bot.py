import os
import requests
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRYPTO") 

# --- CONFIGURACIÓN ---
TIMEFRAMES = [
    ("1week", "MENSUAL"),
    ("1week", "SEMANAL"),
    ("1day", "DIARIO")
]
ADX_TH = 20
ESTADO_FILE = "estado_mercado.json"

# --- LISTA DE MONEDAS ---
TOP_COINS = ['BTC', 'ETH']
ALTCOINS = sorted([
    'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'SHIB', 'DOT',
    'LINK', 'TRX', 'MATIC', 'LTC', 'BCH', 'NEAR', 'UNI', 'ICP', 'FIL', 'APT',
    'INJ', 'LDO', 'OP', 'ARB', 'TIA', 'SEI', 'SUI', 'RNDR', 'FET', 'WLD',
    'PEPE', 'BONK', 'WIF', 'FLOKI', 'ORDI', 'SATS', 'GALA', 'SAND', 'MANA',
    'AXS', 'AAVE', 'SNX', 'MKR', 'CRV', 'DYDX', 'JUP', 'PYTH', 'ENA', 'RUNE',
    'FTM', 'ATOM', 'ALGO', 'VET', 'EGLD', 'STX', 'IMX', 'KAS', 'TAO'
])
COINS = TOP_COINS + [c for c in ALTCOINS if c not in TOP_COINS]

# --- PERSISTENCIA (Para el 🆕 NEW) ---
def cargar_estado_anterior():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def guardar_estado_actual(estado):
    try:
        with open(ESTADO_FILE, 'w') as f: json.dump(estado, f)
    except: pass

# --- FUNCIONES DE TELEGRAM ---
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

# --- MOTOR DE DATOS ---
def get_kucoin_data(symbol, k_interval):
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {'symbol': f"{symbol}-USDT", 'type': k_interval, 'limit': 1000 if k_interval=='1week' else 400}
    try:
        r = requests.get(url, params=params, timeout=5).json()
        if r['code'] == '200000':
            df = pd.DataFrame(r['data'], columns=['Time','Open','Close','High','Low','Vol','Turn']).astype(float)
            df['Time'] = pd.to_datetime(df['Time'], unit='s')
            return df.sort_values('Time').reset_index(drop=True)
    except: pass
    return pd.DataFrame()

def resample_to_monthly(df_weekly):
    if df_weekly.empty: return pd.DataFrame()
    df_temp = df_weekly.set_index('Time')
    try:
        df_monthly = df_temp.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    except:
        df_monthly = df_temp.resample('M').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    return df_monthly.reset_index()

# --- INDICADORES ---
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
    def wilder(x, n): return x.ewm(alpha=1/n, adjust=False).mean()
    tr_s = wilder(df['TR'], period).replace(0, 1)
    p_di, n_di = 100*(wilder(df['+DM'], period)/tr_s), 100*(wilder(df['-DM'], period)/tr_s)
    dx = 100 * abs(p_di - n_di) / (p_di + n_di)
    return wilder(dx, period)

def get_last_signal(df, adx_th):
    if len(df) < 20: return None
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    last_signal, in_pos = None, False
    for i in range(1, len(df_ha)):
        c, a, d, p = df_ha['Color'].iloc[i], df['ADX'].iloc[i], df_ha['Time'].iloc[i], df_ha['Close'].iloc[i]
        if not in_pos and c == 1 and a > adx_th:
            in_pos, last_signal = True, {"Tipo": "🟢 LONG", "Fecha": d, "Precio": p, "ADX": a, "Color": 1}
        elif in_pos and c == -1:
            in_pos, last_signal = False, {"Tipo": "🔴 SHORT", "Fecha": d, "Precio": p, "ADX": a, "Color": -1}
    if not last_signal:
        curr = df_ha.iloc[-1]
        last_signal = {"Tipo": "🟢 LONG" if curr['Color']==1 else "🔴 SHORT", "Fecha": curr['Time'], "Precio": curr['Close'], "ADX": df['ADX'].iloc[-1], "Color": curr['Color']}
    return last_signal

# --- EJECUCIÓN PRINCIPAL ---
def run_bot():
    print(f"--- SCAN: {datetime.now()} ---")
    send_message("⚡ **INICIANDO ESCANEO...**")
    
    estado_anterior = cargar_estado_anterior()
    master_data = {}
    estado_para_guardar = {}

    for k_int, label in TIMEFRAMES:
        for coin in COINS:
            try:
                if coin not in master_data:
                    master_data[coin] = {'MENSUAL': None, 'SEMANAL': None, 'DIARIO': None, 'Price': 0, 'LastDate': datetime(2000,1,1)}
                df = get_kucoin_data(coin, k_int)
                if label == "MENSUAL": df = resample_to_monthly(df)
                if df.empty: continue
                sig = get_last_signal(df, ADX_TH)
                if sig:
                    master_data[coin][label] = sig
                    if label == 'DIARIO': master_data[coin]['Price'] = sig['Precio']
                    if sig['Fecha'] > master_data[coin]['LastDate']: master_data[coin]['LastDate'] = sig['Fecha']
                time.sleep(0.01)
            except: pass

    sorted_coins = sorted(master_data.items(), key=lambda x: x[1]['LastDate'], reverse=True)

    # --- 1. REPORTE: MAPA ---
    categories = {"🚀 FULL BULL": [], "💎 PULLBACK": [], "🌱 NACIENDO": [], "🩸 FULL BEAR": [], "🌀 MIXTAS": []}
    icon_map = {1: "🟢", -1: "🔴", 0: "⚪"}

    for t, d in sorted_coins:
        m, w, day = (d['MENSUAL']['Color'] if d['MENSUAL'] else 0), (d['SEMANAL']['Color'] if d['SEMANAL'] else 0), (d['DIARIO']['Color'] if d['DIARIO'] else 0)
        estado_para_guardar[t] = [m, w, day]
        es_nuevo = " 🆕" if [m, w, day] != estado_anterior.get(t, [0, 0, 0]) else ""
        line = f"• {t}: ${d['Price']:,.2f} [{icon_map[m]}{icon_map[w]}{icon_map[day]}]{es_nuevo}"
        
        if m==1 and w==1 and day==1: categories["🚀 FULL BULL"].append(line)
        elif m==1 and w==1 and day==-1: categories["💎 PULLBACK"].append(line)
        elif m<=0 and w==1 and day==1: categories["🌱 NACIENDO"].append(line)
        elif m==-1 and w==-1 and day==-1: categories["🩸 FULL BEAR"].append(line)
        else: categories["🌀 MIXTAS"].append(line)

    map_msg = f"🦄 **MAPA DE MERCADO** ({datetime.now().strftime('%d/%m')})\n\n"
    for cat in categories:
        if categories[cat]: map_msg += f"**{cat}**\n" + "\n".join(categories[cat]) + "\n\n"
    send_message(map_msg)
    guardar_estado_actual(estado_para_guardar)

    # --- 2. REPORTE: BITÁCORA (Ficha por Activo) ---
    log_msg = "📋 **BITÁCORA TÉCNICA**\n*(Precios corresponden a la señal)*\n\n"
    for t, d in sorted_coins:
        if not d['DIARIO'] and not d['SEMANAL']: continue
        ficha = f"**{t}** | Actual: ${d['Price']:,.2f}\n"
        ficha += f"📅 Últ. Actividad: {d['LastDate'].strftime('%d/%m/%Y')}\n"
        for tf in ["DIARIO", "SEMANAL", "MENSUAL"]:
            s = d[tf]
            if s:
                # Aquí agregamos el precio de la señal: s['Precio']
                ficha += f"• **{tf[0]}**: {s['Tipo']} | @ ${s['Precio']:,.2f} | ADX: {s['ADX']:.1f} | {s['Fecha'].strftime('%d/%m/%y')}\n"
            else:
                ficha += f"• **{tf[0]}**: Sin datos\n"
        log_msg += ficha + "\n"
        if len(log_msg) > 3500:
            send_message(log_msg); log_msg = ""; time.sleep(0.5)

    if log_msg: send_message(log_msg)
    send_message("✅ **Escaneo completado.**")

if __name__ == "__main__":
    run_bot()
