import os
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- TELEGRAM ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_CRYPTO")

# --- CONFIG ---
ADX_TH = 20

# --- CRIPTO MAP (CoinGecko IDs) ---
COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "NEAR": "near",
    "FTM": "fantom"
}

# --- TELEGRAM ---
def send_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    time.sleep(0.5)

# --- COINGECKO OHLC ---
def get_ohlc(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    try:
        r = requests.get(url, params={"vs_currency": "usd", "days": days}, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame()

        df = pd.DataFrame(r.json(), columns=["Time","Open","High","Low","Close"])
        df["Time"] = pd.to_datetime(df["Time"], unit="ms")
        return df.astype(float)
    except:
        return pd.DataFrame()

# --- HEIKIN ASHI ---
def heikin_ashi(df):
    ha = df.copy()
    ha["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha["HA_Close"].iloc[i-1]) / 2)
    ha["HA_Open"] = ha_open
    ha["Color"] = np.where(ha["HA_Close"] > ha["HA_Open"], 1, -1)
    return ha

# --- ADX ---
def adx(df, n=14):
    df = df.copy()
    df["TR"] = np.maximum(
        df["High"] - df["Low"],
        np.maximum(abs(df["High"] - df["Close"].shift()),
                   abs(df["Low"] - df["Close"].shift()))
    )

    df["+DM"] = np.where(
        (df["High"] - df["High"].shift()) > (df["Low"].shift() - df["Low"]),
        np.maximum(df["High"] - df["High"].shift(), 0), 0
    )

    df["-DM"] = np.where(
        (df["Low"].shift() - df["Low"]) > (df["High"] - df["High"].shift()),
        np.maximum(df["Low"].shift() - df["Low"], 0), 0
    )

    def wilder(x): return x.ewm(alpha=1/n, adjust=False).mean()

    tr = wilder(df["TR"]).replace(0, 1)
    p = 100 * wilder(df["+DM"]) / tr
    m = 100 * wilder(df["-DM"]) / tr
    dx = 100 * abs(p - m) / (p + m)
    return wilder(dx)

# --- SEÑAL ---
def get_signal(df):
    df["ADX"] = adx(df)
    ha = heikin_ashi(df)
    last = ha.iloc[-1]

    if last["Color"] == 1 and df["ADX"].iloc[-1] > ADX_TH:
        return 1, last["Close"]
    else:
        return -1, last["Close"]

# --- MAIN ---
def run_bot():
    bull, bear = [], []

    for sym, cid in COINS.items():
        # mensual ≈ 30d
        df_m = get_ohlc(cid, 30)
        df_w = get_ohlc(cid, 7)
        df_d = get_ohlc(cid, 1)

        if df_m.empty or df_w.empty or df_d.empty:
            continue

        m, _ = get_signal(df_m)
        w, _ = get_signal(df_w)
        d, price = get_signal(df_d)

        line = f"• {sym}: ${price:.2f}"

        if m == -1 and w == -1 and d == -1:
            bear.append(line)
        if m == 1 and w == 1 and d == 1:
            bull.append(line)

        time.sleep(1.2)  # límite CoinGecko

    msg = f"₿ MAPA CRIPTO ({datetime.now().strftime('%d/%m')})\n\n"

    if bear:
        msg += "🩸 FULL BEAR\n" + "\n".join(bear) + "\n\n"
    if bull:
        msg += "🚀 FULL BULL\n" + "\n".join(bull) + "\n\n"

    if not bull and not bear:
        msg += "ℹ️ Mercado mixto / sin alineación total"

    send_message(msg)
    send_message("✅ Fin reporte Cripto")

if __name__ == "__main__":
    run_bot()
