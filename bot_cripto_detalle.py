import ccxt
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime

# --- 1. CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# OJO: Usamos la variable NUEVA para el chat distinto
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRIPTO_DETALLE")

# --- 2. CONFIGURACIÓN ---
# Triada Cripto: 4 Horas, Diario, Semanal
TIMEFRAMES = [
    ('4h', '4H', 150),  
    ('1d', 'D', 150),
    ('1w', 'S', 150)
]

# --- 3. MOTOR DE DATOS (KUCOIN FUTURES) ---
def get_exchange():
    return ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })

def get_top_assets(limit=35):
    """Busca las monedas con más volumen en tiempo real"""
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s in tickers:
            # Filtro: USDT, Swap, Activo
            if tickers[s].get('quoteVolume') and '/USDT:USDT' in s:
                valid.append({
                    'symbol': s,
                    'vol': tickers[s]['quoteVolume']
                })
        
        # Ordenar por volumen
        df = pd.DataFrame(valid).sort_values('vol', ascending=False).head(limit)
        return df['symbol'].tolist()
    except:
        # Fallback de emergencia
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT']

# --- 4. ENVÍO ---
def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: 
        print("Error credenciales")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    if len(message) < 4000:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
    else:
        parts = message.split('\n\n')
        buffer = ""
        for part in parts:
            if len(buffer) + len(part) + 4 > 4000:
                requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": buffer, "parse_mode": "Markdown"})
                time.sleep(1)
                buffer = part + "\n\n"
            else:
                buffer += part + "\n\n"
        if buffer:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": buffer, "parse_mode": "Markdown"})

# --- 5. INDICADORES ---
def calculate_strategy(df):
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    
    # Heikin Ashi
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha_close.iloc[i-1]) / 2)
    
    df['Hist'] = hist
    df['HA_Color'] = np.where(ha_close > ha_open, 1, -1)
    return df

def get_last_signal(df):
    if df.empty: return "N/A", 0, None
    position = "FLAT"
    entry_price = 0.0
    entry_date = df['Timestamp'].iloc[0]
    
    for i in range(1, len(df)):
        c_ha = df['HA_Color'].iloc[i]
        c_hist = df['Hist'].iloc[i]
        p_hist = df['Hist'].iloc[i-1]
        
        curr_date = df['Timestamp'].iloc[i]
        curr_price = df['Close'].iloc[i]
        
        if position == "LONG" and c_hist < p_hist: position = "FLAT"
        if position == "SHORT" and c_hist > p_hist: position = "FLAT"
        
        if position == "FLAT":
            if c_ha == 1 and c_hist < 0 and c_hist > p_hist:
                position = "LONG"
                entry_date = curr_date
                entry_price = curr_price
            elif c_ha == -1 and c_hist > 0 and c_hist < p_hist:
                position = "SHORT"
                entry_date = curr_date
                entry_price = curr_price
                
    if position == "LONG":
        return "🟢 LONG", entry_price, entry_date
    elif position == "SHORT":
        return "🔴 SHORT", entry_price, entry_date
    else:
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        ha_icon = "🟢" if last_row['HA_Color'] == 1 else "🔴"
        macd_icon = "🟢" if last_row['Hist'] > prev_row['Hist'] else "🔴"
        return f"⚪ (HA {ha_icon}|MACD {macd_icon})", last_row['Close'], last_row['Timestamp']

# --- 6. MOTOR PRINCIPAL ---
def run_analysis():
    print("⏳ Conectando a KuCoin...")
    ex = get_exchange()
    tickers = get_top_assets(limit=40) # Top 40 Activos
    
    master_data = {}
    
    for symbol in tickers:
        print(f"-> Analizando {symbol}...")
        clean_name = symbol.replace(':USDT', '').replace('/USDT', '')
        master_data[clean_name] = {}
        
        for tf_code, label, limit in TIMEFRAMES:
            try:
                ohlcv = ex.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit)
                if not ohlcv: continue
                
                df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
                
                # Precio actual (usamos el del 4H para referencia rápida)
                if label == '4H': 
                    master_data[clean_name]['Current_Price'] = df['Close'].iloc[-1]
                
                df = calculate_strategy(df)
                sig, price, date = get_last_signal(df)
                
                master_data[clean_name][label] = {
                    'Signal': sig,
                    'Entry_Price': price,
                    'Date': date
                }
            except: pass
        
        time.sleep(0.1) # Respetar API

    # --- 7. REPORTE ---
    print("⚙️ Generando reporte...")
    report_list = []
    
    for t, info in master_data.items():
        if 'Current_Price' not in info or not all(k in info for k in ['4H','D','S']): continue
        
        dates = [info['4H']['Date'], info['D']['Date'], info['S']['Date']]
        valid_dates = [d for d in dates if d is not None]
        if not valid_dates: continue
        
        max_date = max(valid_dates)
        
        has_new_active_signal = False
        
        lines = []
        lines.append(f"🔹 **{t}** | ${info['Current_Price']:.4f}")
        
        for tf in ['4H', 'D', 'S']:
            data = info[tf]
            sig = data['Signal']
            price = data['Entry_Price']
            date_obj = data['Date']
            
            # Fecha Inteligente (Hora si es hoy, Fecha si es viejo)
            now = datetime.now()
            if date_obj.date() == now.date():
                date_str = date_obj.strftime('%H:%M')
            else:
                date_str = date_obj.strftime('%d/%m')
            
            is_newest = (date_obj == max_date)
            is_active = "LONG" in sig or "SHORT" in sig
            
            # Highlight si es NUEVO y ACTIVO (No neutro)
            should_highlight = is_newest and is_active
            if should_highlight: has_new_active_signal = True
            
            prefix = "🆕 " if should_highlight else ""
            fmt = "**" if should_highlight else ""
            
            # Si es Neutro, ocultamos fecha para limpieza
            if "⚪" in sig:
                line_str = f"{prefix}{tf} {sig} | ${price:.4f}"
            else:
                line_str = f"{prefix}{tf} {sig} | ${price:.4f} | {date_str}"
            
            lines.append(f"{fmt}{line_str}{fmt}")
            
        report_list.append({
            'sort_date': max_date,
            'is_priority': has_new_active_signal,
            'text': "\n".join(lines)
        })
    
    report_list.sort(key=lambda x: (x['is_priority'], x['sort_date']), reverse=True)
    
    final_msg = f"⚡ **DETALLE CRIPTO SYSTEMATRADER**\n📅 {datetime.now().strftime('%d/%m %H:%M')}\n[4H Día Sem]\n\n"
    body = "\n\n".join([item['text'] for item in report_list])
    
    send_telegram_msg(final_msg + body)
    print("✅ Reporte enviado.")

if __name__ == "__main__":
    run_analysis()
