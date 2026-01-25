def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        # MACD
        macd = ta.macd(df["close"])
        df["Hist"] = macd["MACDh_12_26_9"]
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]

        # Heikin Ashi
        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        ha_verde = last["HA_Color"] == 1
        ha_rojo = last["HA_Color"] == -1

        hist_sube = last["Hist"] > prev["Hist"]
        hist_baja = last["Hist"] < prev["Hist"]

        prev_ha_verde = prev["HA_Color"] == 1
        prev_ha_rojo = prev["HA_Color"] == -1
        prev_hist_sube = prev["Hist"] > df.iloc[-3]["Hist"]
        prev_hist_baja = prev["Hist"] < df.iloc[-3]["Hist"]

        long_cond = ha_verde and hist_sube
        short_cond = ha_rojo and hist_baja

        prev_long = prev_ha_verde and prev_hist_sube
        prev_short = prev_ha_rojo and prev_hist_baja

        # ALERTA SOLO SI ES NUEVA
        signal = "—"
        signal_time = "—"

        if long_cond and not prev_long:
            signal = "🟢 LONG CONFIRMADO"
            signal_time = (last["dt"] - pd.Timedelta(hours=3)).strftime("%H:%M")

        elif short_cond and not prev_short:
            signal = "🔴 SHORT CONFIRMADO"
            signal_time = (last["dt"] - pd.Timedelta(hours=3)).strftime("%H:%M")

        rsi = ta.rsi(df["close"], length=14).iloc[-1]
        rsi_val = round(rsi, 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"]]
        last_cross = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "signal": f"{signal} | {rsi_state} ({rsi_val})",
            "m0": "SOBRE 0" if last["MACD"] > 0 else "BAJO 0",
            "h_dir": "ALCISTA" if hist_sube else "BAJISTA",
            "cross_time": last_cross,
            "signal_time": signal_time
        }

    except:
        return None
