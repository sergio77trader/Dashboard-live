import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import re

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Crypto-Radar: Binance Edition")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    .crypto-card {
        background-color: #1e2329; /* Color Binance Dark */
        border: 1px solid #474d57;
        padding: 15px; border-radius: 8px;
        text-align: center; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .signal-box {
        padding: 5px; border-radius: 4px; font-weight: bold; 
        text-align: center; margin-top: 10px; font-size: 0.9rem;
    }
    .sig-long { background-color: rgba(14, 203, 129, 0.15); color: #0ecb81; border: 1px solid #0ecb81; } /* Binance Green */
    .sig-short { background-color: rgba(246, 70, 93, 0.15); color: #f6465d; border: 1px solid #f6465d; } /* Binance Red */
    .sig-wait { background-color: rgba(132, 142, 156, 0.15); color: #848e9c; border: 1px solid #848e9c; }
    
    .alert-pill { font-size: 0.7rem; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; }
    .sqz-anim { animation: pulse 1.5s infinite; color: #F0B90B; border: 1px solid #F0B90B; } /* Binance Yellow */
    
    @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
    
    .audit-item { font-size: 0.85rem; margin-bottom: 4px; border-bottom: 1px solid #333; padding-bottom: 2px; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS BINANCE FUTURES (USDT) ---
CRYPTO_DB = {
    '👑 Majors': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT'],
    '🐸 Memes': ['DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'WIFUSDT', 'FLOKIUSDT', 'BONKUSDT', 'POPCATUSDT', 'BOMEUSDT', 'MEMEUSDT'],
    '🤖 AI & DePIN': ['FETUSDT', 'RNDRUSDT', 'TAOUSDT', 'WLDUSDT', 'ARKMUSDT', 'NEARUSDT', 'ICPUSDT', 'JASMYUSDT', 'GRTUSDT'],
    '⚡ Layer 2': ['ARBUSDT', 'OPUSDT', 'MATICUSDT', 'IMXUSDT', 'STXUSDT', 'MANTLEUSDT', 'STRKUSDT'],
    '🔗 DeFi': ['UNIUSDT', 'AAVEUSDT', 'LDOUSDT', 'MKRUSDT', 'JUPUSDT', 'ENAUSDT', 'RUNEUSDT', 'CRVUSDT'],
    '🎮 Gaming': ['SANDUSDT', 'MANAUSDT', 'AXSUSDT', 'GALAUSDT', 'APEUSDT', 'BEAMXUSDT', 'PIXELUSDT'],
    '👵 Legacy': ['LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'XMRUSDT', 'XLMUSDT', 'EOSUSDT']
}

if 'binance_data' not in st.session_state: st.session_state['binance_data'] = []

# --- CONEXIÓN BINANCE API (FUTURES) ---
def get_binance_klines(symbol, interval='1d', limit=100):
    """Conecta directamente a Binance Futures"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        # Binance devuelve listas, no dicts. Convertimos a DF.
        # Estructura: [Open Time, Open, High, Low, Close, Volume, ...]
        df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QVol', 'Trades', 'TakerBuyBase', 'TakerBuyQuote', 'Ignore'])
        
        # Convertir a float
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df[cols] = df[cols].astype(float)
        
        return df
    except Exception as e:
        return pd.DataFrame()

# --- INDICADORES TÉCNICOS ---
def calculate_indicators(df):
    try:
        # EMAs
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        
        # ADX (Fuerza)
        df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        df['ATR'] = df['TR'].rolling(14).mean()
        
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        df['DI+'] = 100 * (plus_dm.ewm(alpha=1/14).mean() / df['ATR'])
        df['DI-'] = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / df['ATR'])
        df['DX'] = 100 * abs(df['DI+'] - df['DI-']) / (df['DI+'] + df['DI-'])
        df['ADX'] = df['DX'].rolling(14).mean()
        
        # Bollinger Squeeze
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['StdDev'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (2 * df['StdDev'])
        df['Lower'] = df['SMA20'] - (2 * df['StdDev'])
        df['BandWidth'] = (df['Upper'] - df['Lower']) / df['SMA20']
        
        # RVOL (Relative Volume)
        df['VolAvg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['VolAvg']
        
        return df
    except: return pd.DataFrame()

# --- CONTEXTO MACRO (BTC & ETH/BTC) ---
def get_macro_context():
    try:
        # 1. Bitcoin Trend
        btc_df = get_binance_klines("BTCUSDT", interval='1d', limit=60)
        if btc_df.empty: return "NEUTRAL", 0, 0
        
        btc_df['EMA50'] = btc_df['Close'].ewm(span=50).mean()
        btc_last = btc_df.iloc[-1]
        
        btc_trend = "ALCISTA" if btc_last['Close'] > btc_last['EMA50'] else "BAJISTA"
        btc_price = btc_last['Close']
        
        # 2. ETH/BTC (Altseason Proxy) - Binance tiene el par ETHBTC
        pair_df = get_binance_klines("ETHBTC", interval='1d', limit=30)
        if pair_df.empty:
            alt_score = 0
        else:
            pair_df['EMA20'] = pair_df['Close'].ewm(span=20).mean()
            pair_last = pair_df.iloc[-1]
            # Si ETH gana a BTC -> Altseason (+1), si pierde -> Bitcoin Season (-1)
            alt_score = 1 if pair_last['Close'] > pair_last['EMA20'] else -1
            
        # Penalización Macro Global
        macro_penalty = 0
        if btc_trend == "BAJISTA": macro_penalty = -2 # Si BTC cae, todo cae
        
        return btc_trend, btc_price, macro_penalty + alt_score
        
    except: return "NEUTRAL", 0, 0

# --- ANALIZADOR INDIVIDUAL ---
def analyze_coin(ticker, macro_adjustment):
    try:
        df = get_binance_klines(ticker)
        if df.empty: return None
        
        df = calculate_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 5 # Base
        audit = [] # Lista de explicaciones
        alerts = []
        
        # 1. MACRO AJUSTE
        score += macro_adjustment
        if macro_adjustment < 0: audit.append(f"❌ Entorno Macro Bajista (BTC débil) [{macro_adjustment}]")
        elif macro_adjustment > 0: audit.append(f"✅ Entorno Macro Alcista (Altseason) [+{macro_adjustment}]")
        
        # 2. TENDENCIA (EMA)
        if last['EMA8'] > last['EMA21']:
            score += 2
            audit.append("✅ Tendencia Corto Plazo Alcista (EMA 8>21)")
            if last['Close'] > last['EMA8']:
                score += 1
                audit.append("✅ Momentum Muy Fuerte (Precio > EMA 8)")
        else:
            score -= 2
            audit.append("❌ Tendencia Corto Plazo Bajista")
            
        # 3. FUERZA (ADX)
        if last['ADX'] > 25:
            audit.append(f"💪 Tendencia Sólida (ADX {last['ADX']:.0f} > 25)")
            # Si hay tendencia, el score se radicaliza (para bien o mal)
            score += 1 if score > 5 else -1
        else:
            audit.append(f"💤 Mercado Lateral / Rango (ADX {last['ADX']:.0f})")
            # Pull to neutral
            if score > 5: score -= 1
            if score < 5: score += 1
            
        # 4. VOLUMEN (RVOL)
        if last['RVOL'] > 2.0:
            score += 2 if score > 5 else -2 # Confirma la dirección
            audit.append(f"🔥 Volumen Climático (x{last['RVOL']:.1f} vs promedio)")
            alerts.append(f"VOL x{last['RVOL']:.1f}")
        elif last['RVOL'] < 0.6:
            audit.append("🧊 Poco interés (Volumen bajo)")
            
        # 5. SQUEEZE
        avg_bw = df['BandWidth'].rolling(50).mean().iloc[-1]
        is_sqz = last['BandWidth'] < (avg_bw * 0.9)
        if is_sqz:
            alerts.append("💣 SQUEEZE")
            audit.append("💣 Compresión de Volatilidad (Squeeze): Explosión inminente")
            
        # SEÑAL FINAL
        final_score = max(0, min(10, score))
        
        signal = "ESPERAR ✋"
        sig_type = "sig-wait"
        
        if final_score >= 8 and last['ADX'] > 20: 
            signal = "LONG 🟢"
            sig_type = "sig-long"
        elif final_score <= 2 and last['ADX'] > 20: 
            signal = "SHORT 🔴"
            sig_type = "sig-short"
            
        return {
            "Ticker": ticker,
            "Price": last['Close'],
            "Change": ((last['Close'] - prev['Close']) / prev['Close']) * 100,
            "Signal": signal,
            "Type": sig_type,
            "Score": final_score,
            "RVOL": last['RVOL'],
            "ADX": last['ADX'],
            "Alerts": alerts,
            "Audit": audit
        }
        
    except: return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎛️ Centro de Comando")
    
    # Contexto BTC
    btc_trend, btc_price, macro_adj = get_macro_context()
    btc_color = "#0ecb81" if btc_trend == "ALCISTA" else "#f6465d"
    
    st.markdown(f"""
    <div style='background:#1e2329; padding:10px; border-radius:5px; border:1px solid #474d57; text-align:center;'>
        <div style='color:#848e9c; font-size:0.8rem;'>TENDENCIA BITCOIN</div>
        <div style='color:{btc_color}; font-size:1.3rem; font-weight:bold;'>{btc_trend}</div>
        <div style='color:#fff;'>${btc_price:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Selectores
    lote = st.selectbox("Seleccionar Sector:", list(CRYPTO_DB.keys()))
    
    if st.button("📡 Escanear Sector (Binance)"):
        targets = CRYPTO_DB[lote]
        prog = st.progress(0)
        
        # Filtro de duplicados
        existing = [x['Ticker'] for x in st.session_state['binance_data']]
        run_list = [t for t in targets if t not in existing]
        
        for i, t in enumerate(run_list):
            res = analyze_coin(t, macro_adj)
            if res: st.session_state['binance_data'].append(res)
            prog.progress((i+1)/len(run_list))
            time.sleep(0.1) # Respetar rate limits de Binance (suaves)
        
        prog.empty()
        st.rerun()
        
    st.divider()
    
    # Input Manual Inteligente
    st.markdown("### ✍️ Búsqueda Manual")
    raw_txt = st.text_input("Ticker (Ej: PEPE, BTC, SOL):")
    if st.button("🔎 Buscar"):
        if raw_txt:
            # Limpieza para que funcione siempre
            clean = raw_txt.upper().strip().replace("USDT","").replace("-USD","").replace("USD","")
            target = f"{clean}USDT" # Formato Binance
            
            # Chequear si existe en memoria
            existing = [x['Ticker'] for x in st.session_state['binance_data']]
            if target in existing:
                st.warning("Ya está en pantalla.")
            else:
                with st.spinner(f"Consultando Binance por {target}..."):
                    res = analyze_coin(target, macro_adj)
                    if res: 
                        st.session_state['binance_data'].append(res)
                        st.rerun()
                    else:
                        st.error(f"No se encontró {target} en Futuros.")

    if st.button("🗑️ Limpiar Todo"): st.session_state['binance_data'] = []; st.rerun()

# --- MAIN SCREEN ---
st.title("🛰️ Crypto-Radar: Binance Futures Direct")

if st.session_state['binance_data']:
    data = st.session_state['binance_data']
    
    # Filtros
    c1, c2 = st.columns([3, 1])
    with c1:
        f = st.radio("Filtros:", ["Todos", "Solo LONG 🟢", "Solo SHORT 🔴", "Solo SQUEEZE 💣"], horizontal=True)
        
    filtered = data
    if f == "Solo LONG 🟢": filtered = [x for x in data if "LONG" in x['Signal']]
    elif f == "Solo SHORT 🔴": filtered = [x for x in data if "SHORT" in x['Signal']]
    elif f == "Solo SQUEEZE 💣": filtered = [x for x in data if any("SQUEEZE" in a for a in x['Alerts'])]
    
    # Ordenar por oportunidad (Score lejos de 5)
    filtered.sort(key=lambda x: abs(x['Score']-5), reverse=True)
    
    if not filtered:
        st.info("No hay activos para este filtro.")
    else:
        # GRID LAYOUT
        num_cols = 4
        rows = [filtered[i:i + num_cols] for i in range(0, len(filtered), num_cols)]
        
        for row in rows:
            cols = st.columns(num_cols)
            for i, item in enumerate(row):
                with cols[i]:
                    with st.container(border=True):
                        # Header
                        col_t, col_p = st.columns([1, 1])
                        col_t.markdown(f"**{item['Ticker']}**")
                        p_color = "green" if item['Change'] > 0 else "red"
                        col_p.markdown(f":{p_color}[{item['Change']:+.2f}%]")
                        
                        st.caption(f"${item['Price']}")
                        
                        # Signal Box
                        st.markdown(f'<div class="signal-box {item["Type"]}">{item["Signal"]}</div>', unsafe_allow_html=True)
                        
                        # Alertas
                        alerts_html = ""
                        for a in item['Alerts']:
                            cls = "sqz-anim" if "SQUEEZE" in a else "alert-pill"
                            bg = "#333" # Default dark
                            if "VOL" in a: bg = "#673ab7"
                            if "SQUEEZE" in a: bg = "rgba(240, 185, 11, 0.2)"
                            
                            alerts_html += f'<span class="alert-pill {cls}" style="background:{bg}">{a}</span> '
                        
                        if alerts_html:
                            st.markdown(f'<div style="margin:8px 0;">{alerts_html}</div>', unsafe_allow_html=True)
                        
                        # Footer Info
                        st.markdown(f"""
                        <div style="font-size:0.75rem; color:#666; margin-top:5px; border-top:1px solid #333; padding-top:5px;">
                            RVOL: {item['RVOL']:.1f}x | ADX: {item['ADX']:.0f}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # EXPLICACIÓN DETALLADA (AUDITORÍA)
                        with st.expander("🔎 Ver Análisis"):
                            st.markdown(f"**Score:** {item['Score']}/10")
                            for line in item['Audit']:
                                if "✅" in line or "🔥" in line: st.markdown(f":green[{line}]")
                                elif "❌" in line: st.markdown(f":red[{line}]")
                                elif "💣" in line: st.markdown(f":orange[{line}]")
                                else: st.markdown(f"{line}")

else:
    st.info("👈 Conecta con Binance seleccionando un sector en la izquierda.")
