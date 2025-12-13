import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import requests
from datetime import datetime

# --- TUS CREDENCIALES (Se configuran en GitHub Secrets) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- CONFIGURACIÓN ESTRATEGIA ---
# Aquí defines qué temporalidades quieres escanear en cada ejecución
# Formato: (Intervalo de Yahoo, Etiqueta para el mensaje, Periodo de datos)
TIMEFRAMES = [
    ("1mo", "MENSUAL", "max"),
    ("1wk", "SEMANAL", "5y"),
    ("1d", "DIARIO", "2y")  # Opcional, como pediste
]

ADX_LEN = 14
ADX_TH = 20

# --- BASE DE DATOS (Tu lista completa) ---
TICKERS = [
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'MELI', 'GLOB', 'VIST', 'BIOX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TSM', 'MU',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT',
    'XOM', 'CVX', 'SLB', 'BA', 'CAT', 'GE',
    'BABA', 'JD', 'BIDU', 'PBR', 'VALE', 'ITUB',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'XLE', 'XLF', 'ARKK', 'GLD', 'SLV'
]

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Faltan credenciales.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        prev_open = ha_open[-1]
        prev_close = df_ha['HA_Close'].iloc[i-1]
        ha_open.append((prev_open + prev_close) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def run_scanner():
    print(f"--- INICIANDO ESCANEO: {datetime.now()} ---")
    alerts_buffer = []

    for interval, label, period in TIMEFRAMES:
        print(f"Analizando {label}...")
        
        # Descarga masiva para velocidad
        try:
            data = yf.download(TICKERS, interval=interval, period=period, group_by='ticker', progress=False, auto_adjust=True)
        except:
            print(f"Error descargando datos para {label}")
            continue

        for ticker in TICKERS:
            try:
                # Extraer DF del ticker
                df = data[ticker].dropna() if len(TICKERS) > 1 else data.dropna()
                if df.empty: continue

                # Indicadores
                df.ta.adx(length=ADX_LEN, append=True)
                col_adx = f"ADX_{ADX_LEN}"
                df_ha = calculate_heikin_ashi(df)

                # Lógica de Señal (Cierre de vela anterior vs actual)
                # En TF altos (Mes/Semana), miramos si la vela QUE ACABA DE CERRAR confirmó señal
                # O si la vela actual está dando señal (esto depende de tu preferencia)
                # Aquí miramos la vela -1 (la última disponible, sea cerrada o en curso)
                
                curr = df_ha.iloc[-1]
                prev = df_ha.iloc[-2]
                
                signal = None
                
                # COMPRA: Rojo -> Verde + ADX
                if prev['Color'] == -1 and curr['Color'] == 1 and curr[col_adx] > ADX_TH:
                    signal = "🟢 COMPRA"
                
                # VENTA: Verde -> Rojo
                elif prev['Color'] == 1 and curr['Color'] == -1:
                    signal = "🔴 VENTA"
                
                if signal:
                    alerts_buffer.append(f"**{ticker}** ({label}): {signal}\nPrecio: ${curr['Close']:.2f} | ADX: {curr[col_adx]:.1f}")
                    
            except Exception as e:
                continue

    # Enviar reporte
    if alerts_buffer:
        header = f"🚨 **REPORTE DE MERCADO** 🚨\n{datetime.now().strftime('%d/%m %H:%M')}\n\n"
        body = "\n".join(alerts_buffer)
        
        # Telegram tiene límite de caracteres, si es muy largo lo partimos
        if len(body) > 4000:
            parts = [body[i:i+4000] for i in range(0, len(body), 4000)]
            for p in parts: send_telegram(header + p)
        else:
            send_telegram(header + body)
        
        print(f"Enviadas {len(alerts_buffer)} alertas.")
    else:
        print("Sin cambios de tendencia detectados.")
        # Opcional: Enviar mensaje de "Todo tranquilo" para saber que funciona
        # send_telegram("🤖 Escaneo completado. Sin novedades.")

if __name__ == "__main__":
    run_scanner()
