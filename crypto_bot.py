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
    ("1week", "MENSUAL", 600),
    ("1week", "SEMANAL", 200),
    ("1day", "DIARIO", 300)
]

ADX_TH = 20
ADX_LEN = 14

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

def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def get_kucoin_data(symbol, k_interval):
    url = "https://api.kucoin.com/api/v1/market/candles"
    target = f"{symbol}-USDT"
    limit = 1500 if k_interval == '1week' else 300
    params = {'symbol': target, 'type': k_interval, 'limit': limit}
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
    df_weekly.set_index('Time', inplace=True)
    try:
        df_monthly = df_weekly.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    except:
        df_monthly = df_weekly.resample('M').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    return df_monthly.reset_index()

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
    p_di = 100 * (wilder(df['+DM'], period) / tr_s)
    n_di = 100 * (wilder(df['-DM'], period) / tr_s)
    dx = 100 * abs(p_di - n_di) / (p_di + n_di)
    return wilder(dx, period)

def get_last_signal(df, adx_th):
    if len(df) < 20: return None
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    curr = df_ha.iloc[-1]
    return {
        "Tipo": "🟢 LONG" if curr['Color'] == 1 else "🔴 SHORT",
        "Fecha": curr['Time'],
        "Precio": curr['Close'],
        "ADX": df['ADX'].iloc[-1],
        "Color": int(curr['Color'])
    }

def run_bot():
    print(f"--- SCAN: {datetime.now()} ---")
    send_message("⚡ **INICIANDO ESCANEO DE MERCADO...**")
    
    market_map = {t: {'1mo': 0, '1wk': 0, '1d': 0, 'Price': 0} for t in COINS}

    for k_int, label, _ in TIMEFRAMES:
        for coin in COINS:
            try:
                df = get_kucoin_data(coin, k_int)
                if label == "MENSUAL": df = resample_to_monthly(df)
                if df.empty: continue
                sig = get_last_signal(df, ADX_TH)
                if sig:
                    key = "1mo" if label == "MENSUAL" else "1wk" if label == "SEMANAL" else "1d"
                    market_map[coin][key] = sig['Color']
                    if label == 'DIARIO': market_map[coin]['Price'] = sig['Precio']
                time.sleep(0.05)
            except: pass

    # --- LÓGICA DE CATEGORIZACIÓN MEJORADA ---
    full_bull, pullbacks, starting, bounces, full_bear, mixed = [], [], [], [], [], []
    icon_map = {1: "🟢", -1: "🔴", 0: "⚪"}
    
    for t, d in market_map.items():
        m, w, day, p = d['1mo'], d['1wk'], d['1d'], d['Price']
        if m == 0 and w == 0: continue # Sin datos suficientes
        
        line = f"• {t}: ${p:,.4f} [{icon_map[m]}{icon_map[w]}{icon_map[day]}]"
        
        # 1. TODO VERDE
        if m == 1 and w == 1 and day == 1:
            full_bull.append(line)
        # 2. PULLBACK EN TENDENCIA ALCISTA (M y W verdes, pero diario rojo: OPORTUNIDAD)
        elif m == 1 and w == 1 and day == -1:
            pullbacks.append(line)
        # 3. INICIO DE TENDENCIA (Semanal y Diario arrancan verde, Mensual todavía no)
        elif m <= 0 and w == 1 and day == 1:
            starting.append(line)
        # 4. TODO ROJO
        elif m == -1 and w == -1 and day == -1:
            full_bear.append(line)
        # 5. REBOTE EN TENDENCIA BAJISTA (M y W rojos, pero diario verde)
        elif w == -1 and day == 1:
            bounces.append(line)
        # 6. RESTO DE COMBINACIONES
        else:
            mixed.append(line)

    # --- CONSTRUCCIÓN DEL MENSAJE ---
    msg = f"🦄 **MAPA DE MERCADO** ({datetime.now().strftime('%d/%m %H:%M')})\n"
    msg += "Leyenda: [Mes Sem Dia]\n\n"
    
    if full_bull:
        msg += f"🚀 **FULL BULL** (Fuerza total)\n" + "\n".join(full_bull) + "\n\n"
    if pullbacks:
        msg += f"💎 **PULLBACKS** (Oportunidad Compra)\n" + "\n".join(pullbacks) + "\n\n"
    if starting:
        msg += f"🌱 **NACIENDO** (Cambio tendencia)\n" + "\n".join(starting) + "\n\n"
    if bounces:
        msg += f"⚠️ **REBOTES** (Cuidado, Bearish)\n" + "\n".join(bounces) + "\n\n"
    if full_bear:
        msg += f"🩸 **FULL BEAR** (Evitar)\n" + "\n".join(full_bear) + "\n\n"
    
    # Enviar reporte principal
    send_message(msg)
    
    # Reporte de otros movimientos (opcional, para no saturar)
    if mixed:
        msg_mixed = "🌀 **OTRAS SEÑALES / MIXTO**\n" + "\n".join(mixed[:15]) # Limitado a 15
        send_message(msg_mixed)

    send_message("✅ **Escaneo completado.**")

if __name__ == "__main__":
    run_bot()
