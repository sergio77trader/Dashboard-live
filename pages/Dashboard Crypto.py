import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import re

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Crypto-Radar 360: Sniper V2.4")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    /* Ajuste de métricas para que se vean compactas */
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    
    /* Cajas de Señal */
    .sig-box {
        padding: 5px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 5px;
    }
    .long { background-color: #0f3d0f; color: #4caf50; border: 1px solid #4caf50; }
    .short { background-color: #3d0f0f; color: #f44336; border: 1px solid #f44336; }
    .wait { background-color: #1e1e1e; color: #9e9e9e; border: 1px solid #9e9e9e; }
    
    /* Alertas */
    .alert-sqz { color: #ff9800; font-weight: bold; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
CRYPTO_DB = {
    '👑 Majors': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'AVAX-USD', 'TRX-USD', 'LINK-USD', 'DOT-USD'],
    '🐸 Memes': ['DOGE-USD', 'SHIB-USD', 'PEPE24478-USD', 'WIF-USD', 'FLOKI-USD', 'BONK-USD', 'POPCAT-USD'],
    '🤖 AI': ['FET-USD', 'RNDR-USD', 'TAO22974-USD', 'WLD-USD', 'ARKM-USD', 'NEAR-USD', 'ICP-USD', 'JASMY-USD'],
    '⚡ Layer 2': ['ARB11841-USD', 'OP-USD', 'MATIC-USD', 'IMX-USD', 'STX4847-USD', 'MANTLE-USD'],
    '🔗 DeFi': ['UNI7083-USD', 'AAVE-USD', 'LDO-USD', 'MKR-USD', 'JUP-USD', 'ENA-USD', 'RUNE-USD']
}

if 'crypto_v24' not in st.session_state: st.session_state['crypto_v24'] = []

# --- INDICADORES ---
def calculate_indicators(df):
    try:
        # EMAs
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        
        # ADX (Fuerza)
        df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        df['ATR'] = df['TR'].rolling(14).mean()
        df['DMplus'] = np.where((df['High']-df['High'].shift())>(df['Low'].shift()-df['Low']), np.maximum(df['High']-df['High'].shift(),0), 0)
        df['DMminus'] = np.where((df['Low'].shift()-df['Low'])>(df['High']-df['High'].shift()), np.maximum(df['Low'].shift()-df['Low'],0), 0)
        df['DIplus'] = 100*(df['DMplus'].rolling(14).mean()/df['ATR'])
        df['DIminus'] = 100*(df['DMminus'].rolling(14).mean()/df['ATR'])
        df['DX'] = 100*abs(df['DIplus']-df['DIminus'])/(df['DIplus']+df['DIminus'])
        df['ADX'] = df['DX'].rolling(14).mean()
        
        # Bollinger Squeeze
        df['SMA20'] = df['Close'].rolling(20).mean()
        df['StdDev'] = df['Close'].rolling(20).std()
        df['Upper'] = df['SMA20']+(2*df['StdDev'])
        df['Lower'] = df['SMA20']-(2*df['StdDev'])
        df['BandWidth'] = (df['Upper']-df['Lower'])/df['SMA20']
        
        # RVOL
        df['VolAvg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume']/df['VolAvg']
        
        return df
    except: return pd.DataFrame()

# --- ANALIZADOR ---
def analyze_coin(ticker, df_hist):
    try:
        if df_hist.empty or len(df_hist) < 50: return None
        
        df = calculate_indicators(df_hist.copy())
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Lógica de Auditoría (Explicación paso a paso)
        audit = []
        score = 5
        
        # 1. Tendencia
        trend_msg = ""
        if last['EMA8'] > last['EMA21']:
            score += 2
            trend_msg = "✅ Tendencia Alcista (EMA rápida > lenta)"
            if last['Close'] > last['EMA8']:
                score += 1
                trend_msg += " + Momentum Fuerte"
        else:
            score -= 2
            trend_msg = "❌ Tendencia Bajista"
            if last['Close'] < last['EMA8']:
                score -= 1
                trend_msg += " + Caída Fuerte"
        audit.append(trend_msg)
        
        # 2. Fuerza (ADX)
        adx_msg = ""
        if last['ADX'] > 25:
            adx_msg = f"💪 Tendencia Real (ADX {last['ADX']:.0f} > 25)"
            score += 1 if score > 5 else -1
        else:
            adx_msg = f"💤 Mercado Lateral/Ruido (ADX {last['ADX']:.0f})"
            if score > 5: score -= 1
            if score < 5: score += 1
        audit.append(adx_msg)
        
        # 3. Squeeze
        avg_bw = df['BandWidth'].rolling(50).mean().iloc[-1]
        is_sqz = last['BandWidth'] < (avg_bw * 0.9)
        if is_sqz: audit.append("💣 SQUEEZE: Volatilidad comprimida (Alerta Explosión)")
        
        # 4. Volumen
        rvol = last['RVOL']
        if rvol > 2.0:
            score += 2 if score > 5 else -2
            audit.append(f"🔥 Volumen Climático (x{rvol:.1f} veces el promedio)")
        elif rvol > 1.2:
            audit.append(f"⚡ Volumen Alto (x{rvol:.1f})")
        else:
            audit.append(f"🧊 Volumen Bajo (x{rvol:.1f})")
            
        # Señal
        signal = "ESPERAR"
        sig_type = "wait"
        if score >= 8 and last['ADX'] > 20: signal = "LONG"; sig_type="long"
        elif score <= 2 and last['ADX'] > 20: signal = "SHORT"; sig_type="short"
        
        return {
            "Ticker": ticker.replace("-USD", ""),
            "Price": last['Close'],
            "Change": ((last['Close']-prev['Close'])/prev['Close'])*100,
            "Signal": signal,
            "Type": sig_type,
            "Score": score,
            "Squeeze": is_sqz,
            "Audit": audit,
            "RVOL": rvol
        }
    except: return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.title("🎛️ Crypto Sniper")
    
    # Selector Lote
    lote = st.selectbox("Elegir Sector:", list(CRYPTO_DB.keys()))
    if st.button("📡 Escanear Sector"):
        targets = CRYPTO_DB[lote]
        prog = st.progress(0)
        
        existing = [x['Ticker'] for x in st.session_state['crypto_v24']]
        run_list = [t for t in targets if t.replace("-USD","") not in existing]
        
        if run_list:
            data = yf.download(run_list, period="3mo", group_by='ticker', progress=False)
            new_res = []
            for i, t in enumerate(run_list):
                try:
                    df = data[t].dropna() if len(run_list) > 1 else data.dropna()
                    res = analyze_coin(t, df)
                    if res: new_res.append(res)
                except: pass
                prog.progress((i+1)/len(run_list))
            st.session_state['crypto_v24'].extend(new_res)
        prog.empty()
        
    st.divider()
    
    # MANUAL INPUT FIX
    st.markdown("### ✍️ Lista Manual")
    txt = st.text_area("Ej: BTC, ETH, ADAUSDT, PEPE", height=60)
    if st.button("🔎 Analizar"):
        if txt:
            # 1. Separar por comas o espacios
            raw = re.split(r'[,\s\n]+', txt)
            clean_list = []
            for x in raw:
                if not x: continue
                # Limpieza inteligente
                clean = x.upper().strip()
                clean = clean.replace("USDT", "").replace("USD", "") # Quitar par
                # Mapeo de casos especiales si fuera necesario (ej PEPE)
                if clean == "PEPE": clean = "PEPE24478" # Fix común Yahoo
                
                clean_list.append(f"{clean}-USD") # Agregar formato Yahoo
            
            if clean_list:
                with st.spinner(f"Buscando {len(clean_list)} monedas..."):
                    data = yf.download(clean_list, period="3mo", group_by='ticker', progress=False)
                    new_res = []
                    
                    # Logica para 1 solo activo vs varios
                    if len(clean_list) == 1:
                        t = clean_list[0]
                        if not data.empty:
                            res = analyze_coin(t, data)
                            if res: new_res.append(res)
                            else: st.error(f"No se encontraron datos para {t}")
                    else:
                        for t in clean_list:
                            try:
                                df = data[t].dropna()
                                if not df.empty:
                                    res = analyze_coin(t, df)
                                    if res: new_res.append(res)
                            except: st.warning(f"Fallo al descargar {t}")
                            
                    st.session_state['crypto_v24'].extend(new_res)
                    st.rerun()

    st.divider()
    if st.button("🗑️ Limpiar"): st.session_state['crypto_v24'] = []; st.rerun()

# --- MAIN ---
st.title("🛰️ Crypto-Radar 360: Sniper V2.4")

if st.session_state['crypto_v24']:
    data = st.session_state['crypto_v24']
    
    # Filtros
    c1, c2 = st.columns([3,1])
    with c1:
        f = st.radio("Filtro:", ["Todos", "Solo LONG 🟢", "Solo SHORT 🔴", "Solo SQUEEZE 💣"], horizontal=True)
    
    filtered = data
    if f == "Solo LONG 🟢": filtered = [x for x in data if x['Signal'] == "LONG"]
    elif f == "Solo SHORT 🔴": filtered = [x for x in data if x['Signal'] == "SHORT"]
    elif f == "Solo SQUEEZE 💣": filtered = [x for x in data if x['Squeeze']]
    
    # Ordenar por Score Absoluto (Fuerza)
    filtered.sort(key=lambda x: abs(x['Score']-5), reverse=True)
    
    if not filtered:
        st.info("No hay resultados para este filtro.")
    
    # GRID DE TARJETAS NATIVAS (Para permitir Expanders)
    # Usamos st.columns dentro de un loop para hacer la grilla
    num_cols = 4
    rows = [filtered[i:i + num_cols] for i in range(0, len(filtered), num_cols)]

    for row in rows:
        cols = st.columns(num_cols)
        for i, item in enumerate(row):
            with cols[i]:
                # Contenedor visual
                with st.container(border=True):
                    # Título y Precio
                    col_t, col_p = st.columns([1, 1])
                    col_t.markdown(f"**{item['Ticker']}**")
                    color_p = "green" if item['Change'] > 0 else "red"
                    col_p.markdown(f":{color_p}[{item['Change']:+.2f}%]")
                    
                    st.caption(f"${item['Price']:.4f}")
                    
                    # Caja de Señal
                    sig_html = f"""<div class="sig-box {item['Type']}">{item['Signal']}</div>"""
                    st.markdown(sig_html, unsafe_allow_html=True)
                    
                    # Alertas Visuales
                    if item['Squeeze']:
                        st.markdown('<div class="alert-sqz">💣 SQUEEZE</div>', unsafe_allow_html=True)
                    if item['RVOL'] > 2.0:
                        st.caption(f"🔥 Vol x{item['RVOL']:.1f}")
                    
                    # EL BOTÓN MÁGICO DE EXPLICACIÓN
                    with st.expander("🔎 Ver por qué"):
                        st.markdown(f"**Score:** {item['Score']}/10")
                        for line in item['Audit']:
                            if "✅" in line or "🔥" in line: st.markdown(f":green[{line}]")
                            elif "❌" in line: st.markdown(f":red[{line}]")
                            elif "💣" in line: st.markdown(f":orange[{line}]")
                            else: st.markdown(line)

else:
    st.info("👈 Usa el panel izquierdo para agregar criptomonedas.")
