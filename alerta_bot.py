import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

# --- 1. CREDENCIALES (Configúralas aquí o en variables de entorno) ---
# Si no usas variables de entorno, pon tu token entre comillas directamente
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "TU_CHAT_ID_AQUI")

# --- 2. CONFIGURACIÓN ---
TIMEFRAMES = [
    ("1mo", "1mo", "max"),  # Mes
    ("1wk", "1wk", "10y"),  # Semana
    ("1d", "1d", "5y")      # Día
]

ADX_TH = 20

# --- 3. BASE DE DATOS MAESTRA ---
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

# --- 4. FUNCIÓN DE ENVÍO INTELIGENTE (Smart Splitter) ---
def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Falta configurar Token o Chat ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Si el mensaje es corto, se envía directo
    if len(message) < 4000:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
        return

    # Si es largo, lo dividimos por saltos de línea para no cortar palabras
    lines = message.split('\n')
    buffer = ""
    
    for line in lines:
        if len(buffer) + len(line) + 1 > 4000:
            # Enviar el buffer actual y limpiar
            requests.post(url, data={"chat_id": CHAT_ID, "text": buffer, "parse_mode": "Markdown"})
            time.sleep(1) # Pausa para evitar flood limit
            buffer = line + "\n"
        else:
            buffer += line + "\n"
    
    # Enviar lo que quede en el buffer
    if buffer:
        requests.post(url, data={"chat_id": CHAT_ID, "text": buffer, "parse_mode": "Markdown"})

# --- 5. INDICADORES ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Calculo iterativo rápido para HA Open
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    
    df_ha['HA_Open'] = ha_open
    # 1 = Verde, -1 = Rojo
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
    
    # Media Móvil Exponencial (Wilder)
    def wilder(x, period): return x.ewm(alpha=1/period, adjust=False).mean()

    tr_s = wilder(df['TR'], period).replace(0, 1)
    p_dm_s = wilder(df['+DM'], period)
    n_dm_s = wilder(df['-DM'], period)
    
    p_di = 100 * (p_dm_s / tr_s)
    n_di = 100 * (n_dm_s / tr_s)
    dx = 100 * abs(p_di - n_di) / (p_di + n_di)
    return wilder(dx, period)

# --- 6. MOTOR DE ANÁLISIS ---
def run_scan():
    print(f"🦅 Iniciando escaneo SystemaTrader... {datetime.now()}")
    
    market_state = {t: {} for t in TICKERS}
    
    # Bucle de descarga por temporalidad
    for interval, label_key, period in TIMEFRAMES:
        try:
            print(f"Descargando datos {interval}...")
            # Descarga masiva
            data = yf.download(TICKERS, interval=interval, period=period, group_by='ticker', progress=False, auto_adjust=True, threads=True)
            
            for ticker in TICKERS:
                try:
                    # Manejo de DataFrame MultiIndex
                    if len(TICKERS) > 1:
                        df = data[ticker].dropna()
                    else:
                        df = data.dropna()
                    
                    if df.empty or len(df) < 50: continue

                    # Cálculos
                    df['ADX'] = calculate_adx(df)
                    df_ha = calculate_heikin_ashi(df)
                    
                    last = df_ha.iloc[-1]
                    prev = df_ha.iloc[-2]
                    
                    market_state[ticker][label_key] = {
                        'Color': int(last['Color']),
                        'Prev_Color': int(prev['Color']),
                        'Price': float(last['Close']),
                        'ADX': float(last['ADX'])
                    }
                except Exception as e:
                    continue
        except Exception as e:
            print(f"Error en descarga masiva {interval}: {e}")

    # --- CLASIFICACIÓN ---
    categories = {
        "🌱 NACIMIENTO DE TENDENCIA": [], # M- S+ D+
        "🚀 TENDENCIA ALCISTA (FULL BULL)": [], # M+ S+ D+
        "⚠️ CORRECCIÓN / PULLBACK": [], # M+ S+ D-
        "🩸 TENDENCIA BAJISTA (FULL BEAR)": [], # M- S- D-
        "🐻 INICIO BAJA (REVERSAL)": [] # M+ S- D-
    }
    
    icon_map = {1: "🟢", -1: "🔴"}

    for t, data in market_state.items():
        # Verificamos que tenga las 3 temporalidades
        if not all(k in data for k in ['1mo', '1wk', '1d']): continue
        
        m_col = data['1mo']['Color']
        w_col = data['1wk']['Color']
        d_col = data['1d']['Color']
        
        price = data['1d']['Price']
        adx = data['1d']['ADX']
        
        # Matrioska Visual: [M S D]
        visual = f"[{icon_map[m_col]} {icon_map[w_col]} {icon_map[d_col]}]"
        
        # Nuevo? (Si el diario cambió de ayer a hoy)
        is_new = data['1d']['Color'] != data['1d']['Prev_Color']
        tag = "🆕 " if is_new else ""
        
        line = f"{tag}**{t}** ${price:.2f} {visual} (ADX {adx:.0f})"
        
        # Lógica SystemaTrader
        if m_col == -1 and w_col == 1 and d_col == 1:
            categories["🌱 NACIMIENTO DE TENDENCIA"].append(line)
        elif m_col == 1 and w_col == 1 and d_col == 1:
            categories["🚀 TENDENCIA ALCISTA (FULL BULL)"].append(line)
        elif m_col == 1 and w_col == 1 and d_col == -1:
            categories["⚠️ CORRECCIÓN / PULLBACK"].append(line)
        elif m_col == -1 and w_col == -1 and d_col == -1:
            categories["🩸 TENDENCIA BAJISTA (FULL BEAR)"].append(line)
        elif m_col == 1 and w_col == -1 and d_col == -1:
            categories["🐻 INICIO BAJA (REVERSAL)"].append(line)

    # --- ENVÍO DE REPORTES ---
    
    # 1. Cabecera
    header = f"🦅 **REPORTE SYSTEMATRADER**\n📅 {datetime.now().strftime('%d/%m %H:%M')}\n🔎 *Matrioska: [Mes Sem Dia]*"
    send_telegram_msg(header)
    
    # 2. Enviar categorías (Solo si tienen datos)
    for title, lines in categories.items():
        if lines:
            # Ordenar alfabéticamente
            lines.sort()
            # Construir bloque
            block = f"\n**{title}**\n" + "\n".join(lines)
            send_telegram_msg(block)
            time.sleep(0.5) # Pausa entre categorías para orden

    print("Reporte enviado exitosamente.")

if __name__ == "__main__":
    run_scan()
