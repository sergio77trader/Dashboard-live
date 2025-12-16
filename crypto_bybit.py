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
# Intervalos Bybit: D=Diario, W=Semanal, M=Mensual
TIMEFRAMES = [
    ("D", "DIARIO"),
    ("W", "SEMANAL"),
    ("M", "MENSUAL")
]

ADX_TH = 20
ADX_LEN = 14

# --- LISTA DE CRIPTOS (Futuros USDT) ---
TICKERS = sorted([
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'SHIBUSDT', 'DOTUSDT',
    'LINKUSDT', 'TRXUSDT', 'MATICUSDT', 'LTCUSDT', 'BCHUSDT', 'NEARUSDT', 'UNIUSDT', 'ICPUSDT', 'FILUSDT', 'APTUSDT',
    'INJUSDT', 'LDOUSDT', 'OPUSDT', 'ARBUSDT', 'TIAUSDT', 'SEIUSDT', 'SUIUSDT', 'RNDRUSDT', 'FETUSDT', 'WLDUSDT',
    'PEPEUSDT', 'BONKUSDT', 'WIFUSDT', 'FLOKIUSDT', 'ORDIUSDT', 'SATSUSDT', '1000PEPEUSDT', '1000SHIBUSDT', '1000BONKUSDT',
    'GALAUSDT', 'SANDUSDT', 'MANAUSDT', 'AXSUSDT', 'AAVEUSDT', 'SNXUSDT', 'MKRUSDT', 'CRVUSDT', 'DYDXUSDT', 'JUPUSDT',
    'PYTHUSDT', 'ENAUSDT', 'RUNEUSDT', 'FTMUSDT', 'ATOMUSDT', 'ALGOUSDT', 'VETUSDT', 'EGLDUSDT', 'STXUSDT', 'IMXUSDT'
])

def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: 
        print("❌ Error: Faltan credenciales de Telegram.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # Cortar mensajes largos
        if len(msg) > 4000:
            parts = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for p in parts:
                requests.post(url, data={"chat_id": CHAT_ID, "text": p, "parse_mode": "Markdown"})
                time.sleep(1)
        else:
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except Exception as e: 
        print(f"❌ Error enviando a Telegram: {e}")

# --- MOTOR DE DATOS (BYBIT API) ---
def get_bybit_data(symbol, interval):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": 200 # Necesitamos historia para ADX
    }
    try:
        r = requests.get(url, params=params, timeout=10).json()
        if r['retCode'] == 0:
            raw = r['result']['list']
            # Bybit devuelve orden inverso (Nuevo -> Viejo). Lo invertimos.
            df = pd.DataFrame(raw, columns=['Time','Open','High','Low','Close','Vol','Turn'])
            df = df.astype({'Open':float, 'High':float, 'Low':float, 'Close':float})
            df['Time'] = pd.to_datetime(pd.to_numeric(df['Time']), unit='ms')
            
            # Ordenar cronológicamente (Viejo -> Nuevo)
            df = df.iloc[::-1].reset_index(drop=True)
            return df
        else:
            print(f"⚠️ Bybit error para {symbol}: {r['retMsg']}")
    except Exception as e: 
        print(f"⚠️ Error conexión {symbol}: {e}")
    return pd.DataFrame()

# --- CÁLCULOS MATEMÁTICOS ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    # HA Close
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # HA Open Iterativo
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    
    # Color
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

# --- BÚSQUEDA DE SEÑAL ---
def get_last_signal(df, adx_th):
    # Validar datos suficientes
    if len(df) < 50: return None

    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    
    last_signal = None
    in_pos = False
    
    for i in range(1, len(df_ha)):
        c = df_ha['Color'].iloc[i]
        a = df['ADX'].iloc[i]
        d = df_ha['Time'].iloc[i]
        p = df_ha['Close'].iloc[i]
        
        # COMPRA
        if not in_pos and c == 1 and a > adx_th:
            in_pos = True
            last_signal = {"Tipo": "🟢 LONG", "Fecha": d, "Precio": p, "ADX": a, "Color": 1}
        # VENTA
        elif in_pos and c == -1:
            in_pos = False
            last_signal = {"Tipo": "🔴 SHORT", "Fecha": d, "Precio": p, "ADX": a, "Color": -1}
            
    # Estado actual si no hubo cruce reciente
    if not last_signal:
        curr = df_ha.iloc[-1]
        t = "🟢 LONG" if curr['Color'] == 1 else "🔴 SHORT"
        last_signal = {"Tipo": t, "Fecha": curr['Time'], "Precio": curr['Close'], "ADX": df['ADX'].iloc[-1], "Color": curr['Color']}
        
    return last_signal

# --- EJECUCIÓN ---
def run_bot():
    print(f"--- START CRIPTO SCAN: {datetime.now()} ---")
    send_message("⚡ **INICIANDO ANÁLISIS CRIPTO (BYBIT)...**")
    
    market_map = {t: {} for t in TICKERS}
    all_signals_list = []
    
    # 1. ESCANEO
    for interval, label in TIMEFRAMES:
        print(f"--> Analizando {label}...")
        
        for ticker in TICKERS:
            try:
                df = get_bybit_data(ticker, interval)
                if df.empty: continue
                
                sig = get_last_signal(df, ADX_TH)
                
                if sig:
                    # Guardar para Mapa (Semáforo)
                    market_map[ticker][interval] = sig['Color']
                    if interval == 'D': market_map[ticker]['Price'] = sig['Precio']
                    
                    # Guardar para Bitácora
                    all_signals_list.append({
                        "Ticker": ticker.replace("USDT", ""),
                        "TF": label,
                        "Tipo": sig['Tipo'],
                        "Precio": sig['Precio'],
                        "ADX": sig['ADX'],
                        "Fecha": sig['Fecha'],
                        "Fecha_Str": sig['Fecha'].strftime('%d-%m-%Y')
                    })
            except Exception as e:
                print(f"Error procesando {ticker}: {e}")
            
            # Pequeña pausa para no saturar API
            time.sleep(0.05)

    # --- REPORTE 1: EL MAPA ---
    # Lógica relajada: Si tiene Diario y Semanal, ya entra en el mapa
    full_bull, starting, pullback, full_bear = [], [], [], []
    
    for t, d in market_map.items():
        # Verificamos si al menos tiene D y W (Diario y Semanal)
        if 'D' not in d or 'W' not in d: continue
        
        day = d['D']
        w = d['W']
        # Si tiene Mensual lo usamos, si no asumimos Neutro (0) para no romper
        m = d.get('M', 0)
        
        p = d.get('Price', 0)
        clean_t = t.replace("USDT", "")
        
        # Simbología para el mensaje (si falta mensual ponemos ?)
        ico_m = "🟢" if m==1 else "🔴" if m==-1 else "⚪"
        ico_w = "🟢" if w==1 else "🔴"
        ico_d = "🟢" if day==1 else "🔴"
        
        line = f"• {clean_t}: ${p:,.4f} [{ico_m} {ico_w} {ico_d}]"
        
        if w==1 and day==1: 
            if m==1: full_bull.append(line)
            else: starting.append(line)
        elif w==1 and day==-1: pullback.append(line)
        elif w==-1 and day==-1: full_bear.append(line)

    map_msg = f"₿ **MAPA CRIPTO** ({datetime.now().strftime('%d/%m')})\nLeyenda: [Mes Sem Dia]\n\n"
    if starting: map_msg += f"🌱 **NACIMIENTO**\n" + "\n".join(starting) + "\n\n"
    if full_bull: map_msg += f"🚀 **FULL BULL**\n" + "\n".join(full_bull) + "\n\n"
    if pullback: map_msg += f"⚠️ **CORRECCIÓN**\n" + "\n".join(pullback) + "\n\n"
    if full_bear: map_msg += f"🩸 **FULL BEAR**\n" + "\n".join(full_bear[:15]) + ("\n..." if len(full_bear)>15 else "")
    
    send_message(map_msg)
    time.sleep(2)
    
    # --- REPORTE 2: BITÁCORA ORDENADA ---
    if all_signals_list:
        all_signals_list.sort(key=lambda x: x['Fecha'], reverse=True)
        
        send_message(f"📋 **BITÁCORA DETALLADA**\n(Últimas señales vigentes, ordenadas por fecha):")
        
        # Enviar TODAS
        count = 0
        for s in all_signals_list:
            icon = "🚨" if "SHORT" in s['Tipo'] else "🚀"
            msg = (
                f"{icon} **{s['Ticker']} ({s['TF']})**\n"
                f"**{s['Tipo']}**\n"
                f"Precio: ${s['Precio']}\n"
                f"ADX: {s['ADX']:.1f}\n"
                f"Fecha: {s['Fecha_Str']}"
            )
            send_message(msg)
            time.sleep(0.2)
            count += 1
            
        print(f"Enviados {count} mensajes detallados.")
    else:
        send_message("⚠️ No se encontraron señales. Revisa si la API de Bybit responde.")

    send_message("✅ Reporte Cripto finalizado.")

if __name__ == "__main__":
    run_bot()
