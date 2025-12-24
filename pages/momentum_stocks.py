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
ADX_LEN = 14

# --- BASE DE DATOS COMPLETA ---
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

def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

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
    def wilder(x, p): return x.ewm(alpha=1/p, adjust=False).mean()
    tr_s = wilder(df['TR'], period).replace(0, 1)
    p_di = 100 * (wilder(df['+DM'], period) / tr_s)
    n_di = 100 * (wilder(df['-DM'], period) / tr_s)
    return wilder(100 * abs(p_di - n_di) / (p_di + n_di), period)

def get_last_signal(df, adx_th):
    if len(df) < 20: return None
    df['ADX'] = calculate_adx(df)
    df_ha = calculate_heikin_ashi(df)
    
    last_sig = None
    in_pos = False
    
    for i in range(1, len(df_ha)):
        c = df_ha['Color'].iloc[i]
        a = df['ADX'].iloc[i]
        d = df_ha.index[i]
        p = df_ha['Close'].iloc[i]
        
        if not in_pos and c == 1 and a > adx_th:
            in_pos = True
            last_sig = {"T": "🟢 LONG", "F": d, "P": p, "A": a, "C": 1}
        elif in_pos and c == -1:
            in_pos = False
            last_sig = {"T": "🔴 SHORT", "F": d, "P": p, "A": a, "C": -1}
            
    if not last_sig:
        curr = df_ha.iloc[-1]
        last_sig = {"T": "🟢 LONG" if curr['Color']==1 else "🔴 SHORT", "F": curr.name, "P": curr['Close'], "A": df['ADX'].iloc[-1], "C": int(curr['Color'])}
        
    return last_sig

# --- MOTOR PRINCIPAL ---
def run_bot():
    print(f"--- START SCAN: {datetime.now()} ---")
    send_message("⚡ **INICIANDO ESCANEO DE ACTIVOS (+100)...**")
    
    master_data = {}
    ahora = datetime.now()

    # 1. Descarga y Análisis por Timeframe
    for interval, label, period in TIMEFRAMES:
        print(f"Descargando {label}...")
        try:
            data = yf.download(TICKERS, interval=interval, period=period, group_by='ticker', progress=False, auto_adjust=True)
            for ticker in TICKERS:
                if ticker not in master_data:
                    master_data[ticker] = {'DIARIO': None, 'SEMANAL': None, 'MENSUAL': None, 'Price': 0, 'LastDate': datetime(2000,1,1)}
                
                try:
                    df = data[ticker].dropna() if len(TICKERS) > 1 else data.dropna()
                    if df.empty: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    
                    sig = get_last_signal(df, ADX_TH)
                    
                    if sig:
                        master_data[ticker][label] = sig
                        # Guardamos precio actual si es diario
                        if label == 'DIARIO': master_data[ticker]['Price'] = df['Close'].iloc[-1]
                        
                        # Actualizamos la fecha más reciente detectada en este activo
                        # (Para ordenar el reporte después)
                        # Nota: yfinance usa timezone-aware, necesitamos normalizar para comparar
                        sig_dt = sig['F'].replace(tzinfo=None)
                        if sig_dt > master_data[ticker]['LastDate']:
                            master_data[ticker]['LastDate'] = sig_dt
                except: pass
        except Exception as e:
            print(f"Error general en {label}: {e}")

    # 2. Filtrar y Ordenar (Los más recientes primero)
    active_tickers = [i for i in master_data.items() if i[1]['LastDate'] > datetime(2000,1,1)]
    sorted_tickers = sorted(active_tickers, key=lambda x: x[1]['LastDate'], reverse=True)
    
    # 3. Generar Reporte
    report_msg = f"📋 **REPORTE TÉCNICO ({len(sorted_tickers)} Activos)**\n_Ordenado por actividad reciente_\n\n"
    
    for ticker, info in sorted_tickers:
        # Título de Ficha
        p_now = info['Price'] if info['Price'] > 0 else (info['DIARIO']['P'] if info['DIARIO'] else 0)
        ficha = f"**{ticker}** | ${p_now:,.2f}\n"
        ficha += "━━━━━━━━━━━━━━━━━━\n"
        
        has_data = False
        # Recorremos D -> S -> M
        for tf_key, tf_label in [('DIARIO','D'), ('SEMANAL','S'), ('MENSUAL','M')]:
            s = info[tf_key]
            if s:
                has_data = True
                ball = "🟢" if s['C'] == 1 else "🔴"
                # Si la señal es de hace menos de 3 días, es NUEVA
                sig_date = s['F'].replace(tzinfo=None)
                is_fresh = (ahora - sig_date).days <= 3
                
                linea = f"{ball} **{tf_label}** {s['T']} | ${s['P']:,.2f} | ADX:{s['A']:.0f} | {s['F'].strftime('%d/%m/%y')}"
                
                if is_fresh: ficha += f"🆕 **{linea}**\n"
                else: ficha += f"{linea}\n"
            else:
                ficha += f"⚪ **{tf_label}** | Sin Datos\n"
        
        ficha += "━━━━━━━━━━━━━━━━━━\n\n"
        
        if has_data:
            report_msg += ficha
        
        # Enviar por partes si es muy largo
        if len(report_msg) > 3500:
            send_message(report_msg)
            report_msg = ""
            time.sleep(1) # Pausa técnica

    # Enviar remanente
    if report_msg:
        send_message(report_msg)

    send_message("✅ **Escaneo completado.**")

if __name__ == "__main__":
    run_bot()
