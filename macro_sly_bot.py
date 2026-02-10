import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import requests
import time
import os
from datetime import datetime

# CREDENCIALES
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# BÓVEDA V47 (46 ACTIVOS EXACTOS)
TICKERS_TO_SCAN = [
    "YPF", "PAMP", "VIST", "TGS", "CEPU", "EDN", "GGAL", "BMA", "BFR", "SUPV", "MELI", "GLOB", "TX", "CRESY", "LOMA", "TEO",
    "SPY", "QQQ", "ARKK", "EEM", "EWZ", "FXI", "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLB", "XLU", "XLY", "XLRE",
    "GLD", "SLV", "CPER", "PPLT", "USO", "DX-Y.NYB", "TLT", "HYG", "VNQ", "CORN", "BTC-USD", "ETH-USD", "SOL-USD"
]

MACRO_CONFIG = {
    "1D": {"int": "1d", "per": "2y", "label": "D"},
    "1S": {"int": "1wk", "per": "5y", "label": "S"},
    "1M": {"int": "1mo", "per": "max", "label": "M"}
}

def calculate_heikin_ashi(df):
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    return ha_open, ha_close

def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None, False
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, 0, None, False
    hist = macd['MACDh_12_26_9']
    ha_open, ha_close = calculate_heikin_ashi(df)
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev = hist.iloc[i], hist.iloc[i-1]
        hd, hd_prev = ha_dir[i], ha_dir[i-1]
        longC = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shrtC = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        if longC: state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif shrtC: state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
            
    is_new = False
    if entry_tm is not None and entry_tm >= df.index[-2]: is_new = True
    return state, entry_px, entry_tm, is_new

def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})

def main():
    results_list = []
    for sym in TICKERS_TO_SCAN:
        asset_data = {"symbol": sym, "new_alert": False, "lines": []}
        curr_price = 0
        for tf_key, config in MACRO_CONFIG.items():
            try:
                df = yf.download(sym, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if df.empty: continue
                if tf_key == "1D": curr_price = df['Close'].iloc[-1]
                st_val, px_in, tm_in, is_new = run_sly_engine(df)
                if is_new: asset_data["new_alert"] = True
                if st_val != 0:
                    pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                    icon = "🟢 LONG" if st_val == 1 else "🔴 SHORT"
                    asset_data["lines"].append(f"{config['label']}: {'🆕 ' if is_new else ''}{icon} | {tm_in.strftime('%d/%m')} | {pnl:+.2f}%")
                else: asset_data["lines"].append(f"{config['label']}: ⚪ FUERA | - | -")
            except: continue
        asset_data["price"] = curr_price
        results_list.append(asset_data)
        time.sleep(0.2)

    results_list.sort(key=lambda x: (not x["new_alert"], x["symbol"]))
    
    header = f"🦅 **REPORTE SYSTEMATRADER MACRO**\n📅 {datetime.now().strftime('%d/%m %H:%M')}\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
    body = ""
    for item in results_list:
        body += f"{'🆕 ' if item['new_alert'] else '🔹 '}**{item['symbol']}** | ${item['price']:,.2f}\n" + "\n".join(item["lines"]) + "\n\n"
    
    send_telegram_msg(header + body)

if __name__ == "__main__":
    main()
