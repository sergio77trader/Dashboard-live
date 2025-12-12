import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Crypto-Radar 360: Universal")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    .crypto-card {
        background-color: #1e2329;
        border: 1px solid #474d57;
        padding: 15px; border-radius: 8px;
        text-align: center; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .signal-box {
        padding: 5px; border-radius: 4px; font-weight: bold; 
        text-align: center; margin-top: 10px; font-size: 0.9rem;
    }
    .sig-long { background-color: rgba(14, 203, 129, 0.15); color: #0ecb81; border: 1px solid #0ecb81; }
    .sig-short { background-color: rgba(246, 70, 93, 0.15); color: #f6465d; border: 1px solid #f6465d; }
    .sig-wait { background-color: rgba(132, 142, 156, 0.15); color: #848e9c; border: 1px solid #848e9c; }
    
    .alert-pill { font-size: 0.7rem; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; }
    .sqz-anim { animation: pulse 1.5s infinite; color: #F0B90B; border: 1px solid #F0B90B; }
    @keyframes pulse { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
</style>
""", unsafe_allow_html=True)

# --- DICCIONARIO INTELIGENTE (Traductor de Nombres) ---
# Esto corrige el problema de "No encuentro la moneda"
TICKER_MAP = {
    # Memes complicados
    'PEPE': 'PEPE24478-USD', '1000PEPE': 'PEPE24478-USD',
    'BONK': 'BONK-USD', '1000BONK': 'BONK-USD',
    'SHIB': 'SHIB-USD', '1000SHIB': 'SHIB-USD',
    'WIF': 'WIF-USD', 'FLOKI': 'FLOKI-USD', 'DOGS': 'DOGS2-USD',
    # Majors
    'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'SOL': 'SOL-USD', 'BNB': 'BNB-USD',
    'ADA': 'ADA-USD', 'XRP': 'XRP-USD', 'DOT': 'DOT-USD', 'LINK': 'LINK-USD',
    # AI & Otros
    'RNDR': 'RNDR-USD', 'FET': 'FET-USD', 'TAO': 'TAO22974-USD',
    'WLD': 'WLD-USD', 'NEAR': 'NEAR-USD', 'ICP': 'ICP-USD',
    'MATIC': 'MATIC-USD', 'ARB': 'ARB11841-USD', 'OP': 'OP-USD'
}

# Base de datos predefinida (Ya corregida)
SECTORS = {
    '👑 Majors': ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'XRP', 'AVAX'],
    '🐸 Memes': ['DOGE', 'SHIB', 'PEPE', 'WIF', 'FLOKI', 'BONK', 'POPCAT'],
    '🤖 AI': ['FET', 'RNDR', 'TAO', 'WLD', 'NEAR', 'ICP', 'ARKM'],
    '🔗 DeFi': ['UNI', 'AAVE', 'LDO', 'MKR', 'JUP', 'ENA'],
    '⚡ L2': ['ARB', 'OP', 'MATIC', 'IMX', 'STX', 'MANTLE']
}

if 'univ_data' not in st.session_state: st.session_state['univ_data'] = []

# --- RESOLVER TICKER ---
def resolve_ticker(input_text):
    """Convierte lo que escribas al formato correcto de Yahoo"""
    clean = input_text.upper().strip().replace("USDT", "").replace("-USD", "").replace("USD", "")
    # 1. Buscar en diccionario manual
    if clean in TICKER_MAP:
        return TICKER_MAP[clean], clean
    # 2. Si no está, asumir formato estándar
    return f"{clean}-USD", clean

# --- INDICADORES ---
def calculate_indicators(df):
    try:
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        
        # ADX
        df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift()), abs(df['Low'] - df['Close'].shift())))
        df['ATR'] = df['TR'].rolling(14).mean()
        p_dm = df['High'].diff().clip(lower=0)
        m_dm = df['Low'].diff().clip(upper=0).abs()
        df['ADX'] = (100 * abs((p_dm.ewm(alpha=1/14).mean() - m_dm.ewm(alpha=1/14).mean()) / df['ATR'])).rolling(14).mean() # Aprox
        
        # Squeeze
        sma = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['BW'] = ((sma + 2*std) - (sma - 2*std)) / sma
        
        # RVOL
        df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
        return df
    except: return pd.DataFrame()

# --- CONTEXTO MACRO ---
def get_macro():
    try:
        btc = yf.Ticker("BTC-USD").history(period="3mo")
        if btc.empty: return "NEUTRAL", 0
        btc['EMA50'] = btc['Close'].ewm(span=50).mean()
        last = btc.iloc[-1]
        trend = "ALCISTA" if last['Close'] > last['EMA50'] else "BAJISTA"
        return trend, last['Close']
    except: return "NEUTRAL", 0

# --- ANALIZADOR ---
def analyze(ticker_input):
    yf_symbol, display_name = resolve_ticker(ticker_input)
    
    try:
        df = yf.Ticker(yf_symbol).history(period="6mo")
        if df.empty: return None
        
        df = calculate_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- LÓGICA DE PUNTAJE ---
        score = 5
        audit = []
        alerts = []
        
        # 1. Tendencia
        if last['EMA8'] > last['EMA21']:
            score += 2
            audit.append("✅ Tendencia Alcista (EMA 8 > 21)")
            if last['Close'] > last['EMA8']: score += 1; audit.append("✅ Momentum Fuerte")
        else:
            score -= 2
            audit.append("❌ Tendencia Bajista")
            if last['Close'] < last['EMA8']: score -= 1
            
        # 2. Fuerza (ADX)
        adx = last.get('ADX', 20) # Fallback seguro
        if np.isnan(adx): adx = 20
        
        if adx > 25:
            audit.append(f"💪 Tendencia Real (ADX {adx:.0f})")
            score += 1 if score > 5 else -1
        else:
            audit.append(f"💤 Lateral/Ruido (ADX {adx:.0f})")
            if score > 5: score -= 1
            if score < 5: score += 1
            
        # 3. Volumen
        rvol = last.get('RVOL', 1)
        if np.isnan(rvol): rvol = 1
        
        if rvol > 2.0:
            score += 2 if score > 5 else -2
            audit.append(f"🔥 Volumen Climático (x{rvol:.1f})")
            alerts.append(f"VOL x{rvol:.1f}")
            
        # 4. Squeeze
        avg_bw = df['BW'].rolling(50).mean().iloc[-1]
        is_sqz = last['BW'] < (avg_bw * 0.9)
        if is_sqz:
            alerts.append("💣 SQUEEZE")
            audit.append("💣 Alerta de Explosión (Squeeze)")
            
        # Señal
        signal = "ESPERAR"
        sig_type = "sig-wait"
        final_score = max(0, min(10, score))
        
        if final_score >= 8 and adx > 20: signal = "LONG 🟢"; sig_type="sig-long"
        elif final_score <= 2 and adx > 20: signal = "SHORT 🔴"; sig_type="sig-short"
        
        return {
            "Ticker": display_name,
            "Price": last['Close'],
            "Change": ((last['Close'] - prev['Close'])/prev['Close']) * 100,
            "Signal": signal, "Type": sig_type, "Score": final_score,
            "Alerts": alerts, "Audit": audit, "RVOL": rvol, "ADX": adx
        }
    except Exception as e:
        return None

# --- UI ---
with st.sidebar:
    st.title("🎛️ Centro de Comando")
    
    # Semáforo BTC
    trend, price = get_macro()
    btc_col = "#0ecb81" if trend == "ALCISTA" else "#f6465d"
    st.markdown(f"""
    <div style='background:#1e2329; padding:10px; border-radius:5px; border:1px solid #474d57; text-align:center;'>
        <div style='color:#848e9c; font-size:0.8rem;'>CLIMA BITCOIN</div>
        <div style='color:{btc_col}; font-size:1.3rem; font-weight:bold;'>{trend}</div>
        <div style='color:#fff;'>${price:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Selector Sector
    lote = st.selectbox("Sector:", list(SECTORS.keys()))
    if st.button("📡 Escanear Sector"):
        target_list = SECTORS[lote]
        prog = st.progress(0)
        existing = [x['Ticker'] for x in st.session_state['univ_data']]
        
        for i, t in enumerate(target_list):
            if t not in existing:
                res = analyze(t)
                if res: st.session_state['univ_data'].append(res)
            prog.progress((i+1)/len(target_list))
        st.rerun()
        
    st.divider()
    
    # Manual
    st.markdown("### ✍️ Búsqueda Manual")
    txt = st.text_input("Ticker (Ej: PEPE, BTC):")
    if st.button("🔎 Buscar"):
        if txt:
            # Limpiar memoria si es re-análisis del mismo
            clean_name = txt.upper().replace("USDT","")
            st.session_state['univ_data'] = [x for x in st.session_state['univ_data'] if x['Ticker'] != clean_name]
            
            with st.spinner(f"Analizando {clean_name}..."):
                res = analyze(clean_name)
                if res: 
                    st.session_state['univ_data'].append(res)
                    st.rerun()
                else:
                    st.error(f"No se encontró {clean_name}")

    if st.button("🗑️ Limpiar Todo"): st.session_state['univ_data'] = []; st.rerun()

# --- MAIN ---
st.title("🛰️ Crypto-Radar 360: Universal")

if st.session_state['univ_data']:
    data = st.session_state['univ_data']
    
    # Filtros
    c1, c2 = st.columns([3, 1])
    with c1:
        f = st.radio("Filtro:", ["Todos", "LONG 🟢", "SHORT 🔴", "SQUEEZE 💣"], horizontal=True)
        
    filtered = data
    if f == "LONG 🟢": filtered = [x for x in data if "LONG" in x['Signal']]
    elif f == "SHORT 🔴": filtered = [x for x in data if "SHORT" in x['Signal']]
    elif f == "SQUEEZE 💣": filtered = [x for x in data if any("SQUEEZE" in a for a in x['Alerts'])]
    
    # Ordenar
    filtered.sort(key=lambda x: abs(x['Score']-5), reverse=True)
    
    if not filtered:
        st.info("No hay resultados para este filtro.")
    else:
        # GRID
        cols = st.columns(4)
        for i, row in enumerate(filtered):
            with cols[i % 4]:
                with st.container(border=True):
                    # Header
                    c_t, c_p = st.columns([1,1])
                    c_t.markdown(f"**{row['Ticker']}**")
                    clr = "green" if row['Change']>0 else "red"
                    c_p.markdown(f":{clr}[{row['Change']:+.2f}%]")
                    
                    st.caption(f"${row['Price']}")
                    
                    # Signal
                    st.markdown(f'<div class="signal-box {row["Type"]}">{row["Signal"]}</div>', unsafe_allow_html=True)
                    
                    # Alerts
                    for a in row['Alerts']:
                        cls = "sqz-anim" if "SQUEEZE" in a else "alert-pill"
                        bg = "#673ab7" if "VOL" in a else "#ff980033"
                        st.markdown(f'<span class="alert-pill {cls}" style="background:{bg}">{a}</span>', unsafe_allow_html=True)
                    
                    # Footer
                    st.markdown(f"""
                    <div style="font-size:0.75rem; color:#666; margin-top:5px; border-top:1px solid #333; padding-top:5px;">
                        Score: {row['Score']}/10 | ADX: {row['ADX']:.0f}
                    </div>""", unsafe_allow_html=True)
                    
                    # EXPLICACIÓN PASO A PASO
                    with st.expander("🔎 Ver Análisis"):
                        for line in row['Audit']:
                            if "✅" in line: st.markdown(f":green[{line}]")
                            elif "❌" in line: st.markdown(f":red[{line}]")
                            elif "💣" in line: st.markdown(f":orange[{line}]")
                            else: st.markdown(line)

else:
    st.info("👈 Busca una cripto o escanea un sector.")
