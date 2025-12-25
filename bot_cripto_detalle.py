import ccxt
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime

# --- 1. CREDENCIALES ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRIPTO_DETALLE")

# --- 2. CONFIGURACIÓN ---
# Intradía + Swing + Macro
TIMEFRAMES = [
    ('15m', '15M', 200),
    ('1h',  '1H',  200),
    ('4h',  '4H',  150),
    ('1d',  'D',   150),
    ('1w',  'S',   150)
]

# --- 3. MOTOR DE DATOS (KUCOIN FUTURES) ---
def get_exchange():
    return ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })

def get_top_assets(limit=35):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []

        for s in tickers:
            if tickers[s].get('quoteVolume') and '/USDT:USDT' in s:
                valid.append({
                    'symbol': s,
                    'vol': tickers[s]['quoteVolume']
                })

        df = pd.DataFrame(valid).sort_values('vol', ascending=False).head(limit)
        return df['symbol'].tolist()

    except:
        return [
            'BTC/USDT:USDT',
            'ETH/USDT:USDT',
            'SOL/USDT:USDT',
            'BNB/USDT:USDT',
            'XRP/USDT:USDT'
        ]

# --- 4. ENVÍO TELEGRAM ---
def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error credenciales Telegram")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    if len(message) < 4000:
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        })
    else:
        parts = message.split('\n\n')
        buffer = ""

        for part in parts:
            if len(buffer) + len(part) > 3800:
                requests.post(url, data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": buffer,
                    "parse_mode": "Markdown"
                })
                time.sleep(1)
                buffer = part + "\n\n"
            else:
                buffer += part + "\n\n"

        if buffer:
            requests.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": buffer,
                "parse_mode": "Markdown"
            })

# --- 5. INDICADORES ---
def calculate_strategy(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal

    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]

    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha_close.iloc[i-1]) / 2)

    df['Hist'] = hist
    df['HA_Color'] = np.where(ha_close > ha_open, 1, -1)

    return df

def get_last_signal(df):
    if df.empty or len(df) < 3:
        return "N/A", 0, None

    position = "FLAT"
    entry_price = 0.0
    entry_date = df['Timestamp'].iloc[0]

    for i in range(1, len(df)):
        c_ha = df['HA_Color'].iloc[i]
        c_hist = df['Hist'].iloc[i]
        p_hist = df['Hist'].iloc[i-1]

        curr_date = df['Timestamp'].iloc[i]
        curr_price = df['Close'].iloc[i]

        if position == "LONG" and c_hist < p_hist:
            position = "FLAT"
        if position == "SHORT" and c_hist > p_hist:
            position = "FLAT"

        if position == "FLAT":
            if c_ha == 1 and c_hist < 0 and c_hist > p_hist:
                position = "LONG"
                entry_price = curr_price
                entry_date = curr_date

            elif c_ha == -1 and c_hist > 0 and c_hist < p_hist:
                position = "SHORT"
                entry_price = curr_price
                entry_date = curr_date

    if position == "LONG":
        return "🟢 LONG", entry_price, entry_date
    elif position == "SHORT":
        return "🔴 SHORT", entry_price, entry_date
    else:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ha_icon = "🟢" if last['HA_Color'] == 1 else "🔴"
        macd_icon = "🟢" if last['Hist'] > prev['Hist'] else "🔴"
        return f"⚪ (HA {ha_icon}|MACD {macd_icon})", last['Close'], last['Timestamp']

# --- 6. MOTOR PRINCIPAL ---
def run_analysis():
    print("⏳ Conectando a KuCoin Futures...")
    ex = get_exchange()
    tickers = get_top_assets(limit=40)

    master_data = {}

    for symbol in tickers:
        clean_name = symbol.replace(':USDT', '').replace('/USDT', '')
        master_data[clean_name] = {}

        for tf_code, label, limit in TIMEFRAMES:
            try:
                ohlcv = ex.fetch_ohlcv(symbol, timeframe=tf_code, limit=limit)
                if not ohlcv:
                    continue

                df = pd.DataFrame(
                    ohlcv,
                    columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
                )
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')

                if label == '15M':
                    master_data[clean_name]['Current_Price'] = df['Close'].iloc[-1]

                df = calculate_strategy(df)
                sig, price, date = get_last_signal(df)

                master_data[clean_name][label] = {
                    'Signal': sig,
                    'Entry_Price': price,
                    'Date': date
                }

            except Exception as e:
                continue

        time.sleep(0.15)

    # --- 7. REPORTE ---
    report_list = []

    for asset, info in master_data.items():
        if 'Current_Price' not in info:
            continue

        required_tfs = ['15M', '1H', '4H', 'D', 'S']
        if not all(tf in info for tf in required_tfs):
            continue

        dates = [info[tf]['Date'] for tf in required_tfs if info[tf]['Date']]
        if not dates:
            continue

        max_date = max(dates)
        has_new_active_signal = False

        lines = []
        lines.append(f"🔹 **{asset}** | ${info['Current_Price']:.4f}")

        now = datetime.now()

        for tf in required_tfs:
            data = info[tf]
            sig = data['Signal']
            price = data['Entry_Price']
            date_obj = data['Date']

            is_active = "LONG" in sig or "SHORT" in sig
            is_newest = date_obj == max_date if date_obj else False
            highlight = is_active and is_newest

            if highlight:
                has_new_active_signal = True

            prefix = "🆕 " if highlight else ""
            fmt = "**" if highlight else ""

            if date_obj:
                date_str = date_obj.strftime('%H:%M') if date_obj.date() == now.date() else date_obj.strftime('%d/%m')
            else:
                date_str = ""

            if "⚪" in sig:
                line = f"{prefix}{tf} {sig} | ${price:.4f}"
            else:
                line = f"{prefix}{tf} {sig} | ${price:.4f} | {date_str}"

            lines.append(f"{fmt}{line}{fmt}")

        report_list.append({
            'sort_date': max_date,
            'priority': has_new_active_signal,
            'text': "\n".join(lines)
        })

    report_list.sort(key=lambda x: (x['priority'], x['sort_date']), reverse=True)

    header = (
        "⚡ **DETALLE CRIPTO SYSTEMATRADER**\n"
        f"📅 {datetime.now().strftime('%d/%m %H:%M')}\n"
        "[15M 1H 4H Día Sem]\n\n"
    )

    body = "\n\n".join(item['text'] for item in report_list)
    send_telegram_msg(header + body)

    print("✅ Reporte enviado correctamente.")

# --- 8. EJECUCIÓN ---
if __name__ == "__main__":
    run_analysis()
