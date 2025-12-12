import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import re

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Crypto-Radar 360: Sniper V2")

# --- ESTILOS VISUALES (Ciberpunk / Dark Mode Friendly) ---
st.markdown("""
<style>
    .crypto-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px; border-radius: 10px;
        text-align: center; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .signal-box {
        padding: 5px 10px; border-radius: 5px; font-weight: bold; text-align: center; margin-top: 5px; letter-spacing: 1px;
    }
    .sig-long { background-color: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #3fb950; }
    .sig-short { background-color: rgba(218, 54, 51, 0.2); color: #f85149; border: 1px solid #f85149; }
    .sig-wait { background-color: rgba(139, 148, 158, 0.2); color: #8b949e; border: 1px solid #30363d; }
    
    .alert-pill { font-size: 0.7rem; font-weight: bold; padding: 2px 6px; border-radius: 4px; margin: 2px; display: inline-block; }
    .sqz-anim { animation: pulse 1.5s infinite; color: #ff9b00; border: 1px solid #ff9b00; }
    
    @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS MASIVA (BINANCE FUTURES PROXY) ---
CRYPTO_DB = {
    '👑 Majors (L1)': [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'ADA-USD', 'XRP-USD', 'AVAX-USD', 
        'TRX-USD', 'DOT-USD', 'LINK-USD', 'MATIC-USD', 'TON11419-USD', 'SUI20947-USD', 
        'APT21794-USD', 'NEAR-USD', 'ATOM-USD', 'HBAR-USD', 'ICP-USD', 'KAS-USD', 'SEI-USD'
    ],
    '🐸 Memecoins (Casino)': [
        'DOGE-USD', 'SHIB-USD', 'PEPE24478-USD', 'WIF-USD', 'FLOKI-USD', 'BONK-USD', 
        'BOME-USD', 'MEME-USD', 'DOGS-USD', 'POPCAT-USD', 'BRETT-USD', 'MOG-USD', 'TURBO-USD'
    ],
    '🤖 AI & DePIN': [
        'FET-USD', 'RNDR-USD', 'TAO22974-USD', 'WLD-USD', 'ARKM-USD', 'AGIX-USD', 
        'OCEAN-USD', 'JASMY-USD', 'GRT6719-USD', 'THETA-USD', 'FIL-USD', 'AR-USD'
    ],
    '🔗 DeFi & DEX': [
        'UNI7083-USD', 'AAVE-USD', 'LDO-USD', 'MKR-USD', 'JUP-USD', 'PYTH-USD', 
        'CRV-USD', 'SNX-USD', 'DYDX-USD', 'PENDLE-USD', 'ENA-USD', 'RUNE-USD', 'CAKE-USD'
    ],
    '⚡ Layer 2 & Rollups': [
        'ARB11841-USD', 'OP-USD', 'IMX-USD', 'STX4847-USD', 'MANTLE-USD', 'STRK-USD', 'ZK-USD'
    ],
    '🎮 Gaming & Metaverse': [
        'SAND-USD', 'MANA-USD', 'AXS-USD', 'GALA-USD', 'APE-USD', 'BEAM28298-USD', 
        'ILV-USD', 'PIXEL-USD', 'XAI-USD'
    ],
    '👵 Legacy / PoW': [
        'LTC-USD', 'BCH-USD', 'ETC-USD', 'XMR-USD', 'XLM-USD', 'EOS-USD', 'ZEC-USD', 'DASH-USD'
    ]
}

# --- GESTIÓN DE ESTADO (ACUMULACIÓN) ---
if 'crypto_acc_v2' not in st.session_state: 
    st.session_state['crypto_acc_v2'] = []

# --- INDICADORES TÉCNICOS ---
def calculate_indicators(df):
    try:
        # EMAs
        df['EMA8'] = df['Close'].ewm(span=8, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # ADX (Fuerza)
        df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        df['ATR'] = df['TR'].rolling(14).mean()
        df['DMplus'] = np.where((df['High']-df['High'].shift()) > (df['Low'].shift()-df['Low']), np.maximum(df['High']-df['High'].shift(), 0), 0)
        df['DMminus'] = np.where((df['Low'].shift()-df['Low']) > (df['High']-df['High'].shift()), np.maximum(df['Low'].shift()-df['Low'], 0), 0)
        df['DIplus'] = 100 * (df['DMplus'].rolling(14).mean() / df['ATR'])
        df['DIminus'] = 100 * (df['DMminus'].rolling(14).mean() / df['ATR'])
        df['DX'] = 100 * abs(df['DIplus'] - df['DIminus']) / (df['DIplus'] + df['DIminus'])
        df['ADX'] = df['DX'].rolling(14).mean()
        
        # Bollinger Squeeze
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['StdDev'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20'] + (2 * df['StdDev'])
        df['Lower'] = df['SMA20'] - (2 * df['StdDev'])
        df['BandWidth'] = (df['Upper'] - df['Lower']) / df['SMA20']
        
        # Volumen Relativo
        df['VolAvg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['VolAvg']
        
        return df
    except: return pd.DataFrame()

# --- LÓGICA DE BTC (SEMÁFORO) ---
def get_btc_context():
    try:
        btc = yf.download("BTC-USD", period="3mo", progress=False)
        if btc.empty: return "NEUTRAL", 0
        
        btc['EMA50'] = btc['Close'].ewm(span=50).mean()
        last = btc.iloc[-1]
        trend = "ALCISTA" if last['Close'] > last['EMA50'] else "BAJISTA"
        return trend, last['Close']
    except: return "NEUTRAL", 0

# --- ANÁLISIS INDIVIDUAL ---
def analyze_coin(ticker, df_hist):
    try:
        if df_hist.empty or len(df_hist) < 50: return None
        
        df = calculate_indicators(df_hist.copy())
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 5
        reasons = []
        alerts = []
        
        # 1. Tendencia EMA
        if last['EMA8'] > last['EMA21']: 
            score += 2
            if last['Close'] > last['EMA8']: score += 1
        else:
            score -= 2
            if last['Close'] < last['EMA8']: score -= 1
            
        # 2. ADX (Filtro Ruido)
        if last['ADX'] > 25:
            reasons.append(f"ADX Fuerte ({last['ADX']:.0f})")
            score += 1 if score > 5 else -1
        else:
            reasons.append("Rango/Ruido")
            # Penalización suave al score para llevarlo a neutro
            if score > 5: score -= 1
            if score < 5: score += 1
            
        # 3. Squeeze
        avg_bw = df['BandWidth'].rolling(50).mean().iloc[-1]
        if last['BandWidth'] < (avg_bw * 0.9):
            alerts.append("💣 SQUEEZE")
            
        # 4. Volumen
        if last['RVOL'] > 2.0:
            score += 2 if score > 5 else -2
            alerts.append(f"🔥 VOL x{last['RVOL']:.1f}")
            
        # Señal
        signal = "ESPERAR ✋"
        if score >= 8 and last['ADX'] > 20: signal = "LONG 🟢"
        elif score <= 2 and last['ADX'] > 20: signal = "SHORT 🔴"
        
        return {
            "Ticker": ticker.replace("-USD", ""),
            "Price": last['Close'],
            "Change": ((last['Close'] - prev['Close'])/prev['Close']) * 100,
            "Signal": signal,
            "Score": score,
            "RVOL": last['RVOL'],
            "ADX": last['ADX'],
            "Reasons": " | ".join(reasons),
            "Alerts": alerts
        }
    except: return None

# --- FUNCIÓN DE PROCESAMIENTO CENTRAL ---
def run_scan(target_list):
    prog = st.progress(0)
    st_txt = st.empty()
    
    # 1. Filtrar duplicados que ya están en memoria
    current_tickers = [x['Ticker'] for x in st.session_state['crypto_acc_v2']]
    # Limpiamos el "-USD" para comparar bien, o agregamos para descargar
    clean_targets = []
    for t in target_list:
        clean_t = t.replace("-USD", "").strip()
        if clean_t not in current_tickers:
            clean_targets.append(f"{clean_t}-USD")
    
    if not clean_targets:
        st.toast("⚠️ Esas monedas ya están en la lista.", icon="ℹ️")
        return

    # 2. Descarga Masiva
    st_txt.text(f"Conectando con Binance (vía Yahoo) para {len(clean_targets)} activos...")
    try:
        data = yf.download(clean_targets, period="3mo", group_by='ticker', progress=False)
        
        new_results = []
        for i, t in enumerate(clean_targets):
            st_txt.text(f"Procesando {t}...")
            try:
                if len(clean_targets) > 1: df_coin = data[t]
                else: df_coin = data
                
                df_coin = df_coin.dropna()
                res = analyze_coin(t, df_coin)
                if res: new_results.append(res)
            except: pass
            prog.progress((i+1)/len(clean_targets))
        
        # 3. ACUMULACIÓN (La magia)
        st.session_state['crypto_acc_v2'].extend(new_results)
        st.toast(f"✅ Agregadas {len(new_results)} criptos al tablero.", icon="🚀")
        
    except Exception as e:
        st.error(f"Error: {e}")
    
    st_txt.empty()
    prog.empty()

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎛️ Centro de Comando")
    
    # 1. Semáforo BTC
    trend, price = get_btc_context()
    btc_col = "green" if trend == "ALCISTA" else "red"
    st.markdown(f"**BTC:** <span style='color:{btc_col}'>{trend}</span> (${price:,.0f})", unsafe_allow_html=True)
    st.divider()
    
    # 2. Selector de Lotes
    st.subheader("1. Escáner por Sector")
    narrative = st.selectbox("Selecciona Lote:", list(CRYPTO_DB.keys()))
    if st.button("📡 Escanear Sector"):
        run_scan(CRYPTO_DB[narrative])
        
    st.divider()
    
    # 3. Lista Personalizada
    st.subheader("2. Lista Personalizada")
    custom_txt = st.text_area("Escribe tickers (ej: APT, SUI, DOGE):", height=70)
    if st.button("🔎 Analizar Mi Lista"):
        if custom_txt:
            # Limpieza de input
            raw_list = re.split(r'[,\s\n]+', custom_txt)
            clean_list = [f"{t.upper().strip()}-USD" if not t.upper().endswith("-USD") else t.upper().strip() for t in raw_list if t]
            if clean_list:
                run_scan(clean_list)
            else:
                st.warning("Lista vacía.")
                
    st.divider()
    
    # 4. Gestión
    st.metric("Total Analizado", len(st.session_state['crypto_acc_v2']))
    if st.button("🗑️ Borrar Todo"):
        st.session_state['crypto_acc_v2'] = []
        st.rerun()

# --- VISTA PRINCIPAL ---
st.title("🛰️ Crypto-Radar 360: Sniper V2 (Acumulativo)")

if st.session_state['crypto_acc_v2']:
    df = pd.DataFrame(st.session_state['crypto_acc_v2'])
    
    # Filtros Visuales
    c_f1, c_f2 = st.columns([3, 1])
    with c_f1:
        f_mode = st.radio("Filtro Rápido:", ["Ver Todo", "Solo LONG 🟢", "Solo SHORT 🔴", "Solo SQUEEZE 💣"], horizontal=True)
    
    # Aplicar Filtros
    if f_mode == "Solo LONG 🟢": df = df[df['Signal'].str.contains("LONG")]
    elif f_mode == "Solo SHORT 🔴": df = df[df['Signal'].str.contains("SHORT")]
    elif f_mode == "Solo SQUEEZE 💣": df = df[df['Alerts'].apply(lambda x: "SQUEEZE" in str(x))]
    
    # Ordenar por Score (Lo más fuerte arriba)
    if not df.empty:
        df['AbsScore'] = abs(df['Score'] - 5)
        df = df.sort_values('AbsScore', ascending=False)
    
        # MOSTRAR TARJETAS GRID
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                # Estilos Dinámicos
                sig_class = "sig-long" if "LONG" in row['Signal'] else "sig-short" if "SHORT" in row['Signal'] else "sig-wait"
                price_col = "#3fb950" if row['Change'] > 0 else "#f85149"
                
                # Renderizar Alertas
                alerts_html = ""
                for alert in row['Alerts']:
                    cls = "sqz-anim" if "SQUEEZE" in alert else "alert-pill"
                    bg = "rgba(255, 155, 0, 0.2)" if "SQUEEZE" in alert else "rgba(100, 100, 255, 0.2)"
                    alerts_html += f'<span class="alert-pill {cls}" style="background:{bg}">{alert}</span>'
                
                st.markdown(f"""
                <div class="crypto-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:bold; font-size:1.1rem;">{row['Ticker']}</span>
                        <span style="color:{price_col}; font-weight:bold;">{row['Change']:+.2f}%</span>
                    </div>
                    <div style="font-size:0.9rem; margin-bottom:5px;">${row['Price']:.4f}</div>
                    
                    <div class="signal-box {sig_class}">{row['Signal']}</div>
                    
                    <div style="margin-top:8px;">{alerts_html}</div>
                    
                    <div style="font-size:0.75rem; margin-top:8px; color:#8b949e; border-top:1px solid #30363d; padding-top:5px;">
                        {row['Reasons']}<br>
                        <span style="opacity:0.7">RVOL: {row['RVOL']:.1f}x | ADX: {row['ADX']:.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No hay activos que cumplan con el filtro seleccionado.")

else:
    st.info("👈 Usa el menú lateral para agregar criptomonedas al tablero.")
