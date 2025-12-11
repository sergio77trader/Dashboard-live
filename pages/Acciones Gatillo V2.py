import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader 360: Tactical Edition Fixed")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div[data-testid="stMetric"], .metric-card {
        background-color: transparent !important;
        border: 1px solid #e0e0e0;
        padding: 12px; border-radius: 8px; text-align: center;
        min-height: 150px; display: flex; flex-direction: column; justify-content: center;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"], .metric-card { border: 1px solid #404040; }
    }
    .big-score { font-size: 2rem; font-weight: 800; margin: 5px 0; }
    .score-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; opacity: 0.8; }
    
    .alert-pill {
        font-size: 0.7rem; font-weight: bold; padding: 2px 8px; border-radius: 10px; display: inline-block; margin: 2px;
    }
    .squeeze-alert { background-color: #FF6D00; color: white; animation: pulse 2s infinite; }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
DB_CATEGORIES = {
    '🇦🇷 Argentina': ['GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX'],
    '🇺🇸 Mag 7 & Tech': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR'],
    '🤖 Semis & AI': ['AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML'],
    '🏦 Financiero': ['JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN'],
    '💊 Salud': ['LLY', 'NVO', 'JNJ', 'PFE', 'MRK', 'ABBV', 'UNH', 'BMY', 'AMGN'],
    '🛒 Consumo': ['KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'PG'],
    '🏭 Industria': ['XOM', 'CVX', 'SLB', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'F', 'GM'],
    '🇧🇷 Brasil': ['PBR', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV'],
    '🇨🇳 China': ['BABA', 'JD', 'BIDU', 'PDD', 'NIO'],
    '⛏️ Minería': ['GOLD', 'NEM', 'FCX', 'SCCO'],
    '📈 ETFs': ['SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'XLE', 'XLF', 'XLK', 'XLV', 'ARKK', 'GLD', 'SLV', 'GDX', 'XLY', 'XLP']
}
CEDEAR_DATABASE = sorted(list(set([item for sublist in DB_CATEGORIES.values() for item in sublist])))

# --- ESTADO (V14 - Tactical) ---
if 'st360_db_v14' not in st.session_state: st.session_state['st360_db_v14'] = []

# --- NUEVOS INDICADORES TÁCTICOS (ADX, BANDAS, RVOL) ---

def calculate_adx(df, period=14):
    """Calcula el ADX (Fuerza de la tendencia)"""
    try:
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = pd.DataFrame(df['High'] - df['Low'])
        tr2 = pd.DataFrame(abs(df['High'] - df['Close'].shift(1)))
        tr3 = pd.DataFrame(abs(df['Low'] - df['Close'].shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        atr = tr.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = dx.rolling(period).mean()
        return adx.iloc[-1]
    except: return 0

def check_squeeze(df):
    """Detecta compresión de Bollinger Bands (Energía acumulada)"""
    try:
        sma = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        bandwidth = (upper - lower) / sma
        
        # Si el ancho actual es menor al promedio de 6 meses, es squeeze
        avg_bw = bandwidth.rolling(120).mean().iloc[-1]
        current_bw = bandwidth.iloc[-1]
        
        is_squeeze = current_bw < (avg_bw * 0.8) # 20% más estrecho que lo normal
        return is_squeeze, current_bw
    except: return False, 0

def get_rvol(df):
    """Volumen Relativo (Interés Institucional)"""
    try:
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_curr = df['Volume'].iloc[-1]
        if vol_avg == 0: return 0
        return vol_curr / vol_avg
    except: return 0

# --- MOTORES EXISTENTES (Resumidos) ---
def get_technical_score(df):
    try:
        score = 0; details = []
        # HA
        ha_c = (df['Open']+df['High']+df['Low']+df['Close'])/4
        ha_o = (df['Open'].shift(1)+df['Close'].shift(1))/2
        if ha_c.iloc[-1] > ha_o.iloc[-1]: score+=1; details.append("HA Diario 🟢")
        # Medias
        p = df['Close'].iloc[-1]
        m20 = df['Close'].rolling(20).mean().iloc[-1]
        m50 = df['Close'].rolling(50).mean().iloc[-1]
        if p>m20: score+=1; details.append(">MA20")
        if m20>m50: score+=2; details.append("Tendencia Sana")
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta>0, 0)).rolling(14).mean()
        loss = (-delta.where(delta<0, 0)).rolling(14).mean()
        rsi = 100 - (100/(1+(gain/loss))).iloc[-1]
        if 40<=rsi<=65: score+=2
        elif rsi>70: score-=2
        
        return max(0, min(10, score)), details, rsi
    except: return 0, [], 50

def get_options_data(ticker, price):
    # Opciones (Simplificado para velocidad, misma lógica V12)
    def_res = (5, "Neutro", 0, 0, 0, "N/A", 0)
    try:
        tk = yf.Ticker(ticker); exps = tk.options
        if not exps: return def_res
        opt = tk.option_chain(exps[0]); c=opt.calls; p=opt.puts
        if c.empty or p.empty: return def_res
        
        cw = c.loc[c['openInterest'].idxmax()]['strike']
        pw = p.loc[p['openInterest'].idxmax()]['strike']
        
        t_c, t_p = c['openInterest'].sum(), p['openInterest'].sum()
        pcr = t_p/t_c if t_c > 0 else 0
        sent = "🚀 Euforia" if pcr<0.6 else "🐻 Miedo" if pcr>1.4 else "⚖️ Neutro"
        
        # Max Pain (Aprox rapida)
        strikes = sorted(list(set(c['strike'].tolist()+p['strike'].tolist())))
        rel = [s for s in strikes if price*0.8 < s < price*1.2] or strikes
        cash = []
        for s in rel:
            loss = c.apply(lambda r: max(0,s-r['strike'])*r['openInterest'],1).sum() + \
                   p.apply(lambda r: max(0,r['strike']-s)*r['openInterest'],1).sum()
            cash.append(loss)
        mp = rel[np.argmin(cash)] if cash else price
        
        score = 5
        if price>cw: score=10
        elif price<pw: score=1
        else:
            rng = cw-pw
            if rng>0: score = 10-((price-pw)/rng*10)
            
        return score, "Rango", cw, pw, mp, sent, pcr
    except: return def_res

# --- NUEVO MOTOR TÁCTICO (La Magia) ---
def get_tactical_data(df):
    rvol = get_rvol(df)
    adx = calculate_adx(df)
    is_sqz, bw = check_squeeze(df)
    
    tactical_score = 0
    alerts = []
    
    # RVOL Logic
    if rvol > 2.0: tactical_score += 3; alerts.append(f"🔥 VOLUMEN EXPLOSIVO (x{rvol:.1f})")
    elif rvol > 1.2: tactical_score += 1; alerts.append(f"⚡ Volumen Alto (x{rvol:.1f})")
    elif rvol < 0.6: tactical_score -= 1; alerts.append("🧊 Sin Interés")
    
    # ADX Logic
    if adx > 25: tactical_score += 2; alerts.append(f"💪 Tendencia Fuerte (ADX {adx:.0f})")
    elif adx < 20: tactical_score -= 2; alerts.append("💤 Lateral/Débil")
    
    # Squeeze Logic
    if is_sqz: 
        alerts.append("💣 BOLLINGER SQUEEZE")
        # El squeeze no suma puntos por sí solo (es neutro), pero avisa explosión
    
    return tactical_score, alerts, rvol, adx, is_sqz

# --- ANALISIS COMPLETO ---
def analyze_complete(ticker):
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period="2y") # Necesitamos historia para ADX y Bandas
        if df.empty: return None
        price = df['Close'].iloc[-1]
        
        # 1. Técnico Base
        s_tec, d_tec, rsi = get_technical_score(df)
        
        # 2. Táctico (Energía)
        s_tac, d_tac, rvol, adx, is_sqz = get_tactical_data(df)
        
        # 3. Opciones
        s_opt, _, cw, pw, mp, sent, pcr = get_options_data(ticker, price)
        
        # 4. Estacional (Simplificado)
        curr_m = datetime.now().month
        m_ret = df['Close'].resample('ME').last().pct_change()
        hist = m_ret[m_ret.index.month == curr_m]
        win = (hist>0).mean() if len(hist)>1 else 0
        s_sea = win * 10
        
        # Niveles ATR
        h, l, c = df['High'], df['Low'], df['Close']
        tr = np.maximum((h-l), np.maximum(abs(h-c.shift()), abs(l-c.shift())))
        atr = tr.rolling(14).mean().iloc[-1]
        
        # --- SCORE FINAL RECALIBRADO ---
        # Tec(30%) + Tactico(20%) + Estructura(30%) + Estacional(20%)
        # El Táctico funciona como "Booster"
        raw_score = (s_tec * 3) + (s_opt * 3) + (s_sea * 2) + s_tac
        final = max(0, min(100, raw_score))
        
        verdict = "NEUTRAL"
        if final >= 75: verdict = "🔥 COMPRA FUERTE"
        elif final >= 60: verdict = "✅ COMPRA"
        elif final <= 30: verdict = "💀 VENTA FUERTE"
        elif final <= 45: verdict = "🔻 VENTA"
        
        return {
            "Ticker": ticker, "Price": price, "Score": final, "Verdict": verdict,
            "RSI": rsi, "ATR": atr,
            "S_Tec": s_tec, "D_Tec": d_tec,
            "S_Tac": s_tac, "D_Tac": d_tac, "RVOL": rvol, "ADX": adx, "Squeeze": is_sqz,
            "S_Opt": s_opt, "Sentiment": sent, "CW": cw, "PW": pw, "Max_Pain": mp,
            "S_Sea": s_sea,
            "History": df
        }
    except: return None

# --- UI ---
with st.sidebar:
    st.header("⚙️ TACTICAL CONTROL")
    st.info(f"DB: {len(CEDEAR_DATABASE)} Activos")
    
    batch_size = st.slider("Lote", 1, 15, 5)
    batches = [CEDEAR_DATABASE[i:i + batch_size] for i in range(0, len(CEDEAR_DATABASE), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]}...{b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Elegir Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    c1, c2 = st.columns(2)
    if c1.button("▶️ ESCANEAR", type="primary"):
        targets = batches[sel_batch]
        prog = st.progress(0)
        mem = [x['Ticker'] for x in st.session_state['st360_db_v14']]
        run = [t for t in targets if t not in mem]
        for i, t in enumerate(run):
            r = analyze_complete(t)
            if r: st.session_state['st360_db_v14'].append(r)
            prog.progress((i+1)/len(run))
            time.sleep(0.3)
        prog.empty(); st.rerun()
        
    if c2.button("🗑️ Limpiar"): st.session_state['st360_db_v14'] = []; st.rerun()
    st.divider()
    mt = st.text_input("Ticker:").upper().strip()
    if st.button("Analizar"):
        r = analyze_complete(mt)
        if r: st.session_state['st360_db_v14'].append(r); st.rerun()

st.title("SystemaTrader 360: Tactical Edition 🚀")
st.caption("Radar de Swing Trading: Momentum + Energía + Estructura")

if st.session_state['st360_db_v14']:
    dfv = pd.DataFrame(st.session_state['st360_db_v14'])
    if 'Score' in dfv.columns: dfv = dfv.sort_values("Score", ascending=False)
    
    # Filtros
    with st.expander("🔍 FILTROS TÁCTICOS", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: f_sqz = st.checkbox("🔥 Solo SQUEEZE")
        with c2: f_vol = st.checkbox("⚡ Solo Alto Volumen")
        # FIXED: Valor por defecto en 0 para mostrar todo al inicio
        with c3: f_sco = st.slider("Score Min", 0, 100, 0)
    
    df_show = dfv[dfv['Score'] >= f_sco]
    if f_sqz: df_show = df_show[df_show['Squeeze'] == True]
    if f_vol: df_show = df_show[df_show['RVOL'] > 1.5]
    
    if df_show.empty:
        st.warning(f"⚠️ Se han analizado {len(dfv)} activos, pero los filtros actuales los ocultan todos. Baja el puntaje o quita los checks.")
    else:
        st.dataframe(
            df_show[['Ticker', 'Price', 'Score', 'Verdict', 'RSI', 'RVOL', 'ADX']],
            column_config={
                "Ticker": "Activo", "Price": st.column_config.NumberColumn(format="$%.2f"),
                "Score": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=100, format="%.0f"),
                "RVOL": st.column_config.NumberColumn("Vol. Rel.", format="%.1fx"),
                "ADX": st.column_config.NumberColumn("Fuerza Tend.", format="%.0f"),
            }, use_container_width=True, hide_index=True
        )
    
    st.divider()
    
    # INSPECCIÓN
    l_tickers = df_show['Ticker'].tolist()
    if l_tickers:
        sel = st.selectbox("Inspección Táctica:", l_tickers)
        it = next((x for x in st.session_state['st360_db_v14'] if x['Ticker'] == sel), None)
        
        if it:
            k1, k2, k3, k4 = st.columns(4)
            sc = it['Score']
            clr = "#00C853" if sc >= 70 else "#D32F2F" if sc <= 40 else "#FBC02D"
            
            # Etiquetas dinámicas
            tags_tac = ""
            if it['Squeeze']: tags_tac += '<span class="alert-pill squeeze-alert">💣 SQUEEZE</span> '
            if it['RVOL'] > 1.5: tags_tac += '<span class="alert-pill" style="background:#673AB7; color:white;">⚡ VOLUMEN</span>'
            if it['ADX'] < 20: tags_tac += '<span class="alert-pill" style="background:#9E9E9E; color:white;">💤 LATERAL</span>'
            
            with k1:
                st.markdown(f"""<div class="metric-card"><div class="score-label">TÉCNICO</div><div class="big-score" style="color:#555;">{it['S_Tec']:.1f}</div><div class="sub-info">RSI: {it['RSI']:.1f}</div></div>""", unsafe_allow_html=True)
            with k2:
                st.markdown(f"""<div class="metric-card" style="border:2px solid {clr};"><div class="score-label" style="color:{clr};">SCORE TÁCTICO</div><div class="big-score" style="color:{clr};">{sc:.0f}</div><div style="font-weight:bold; color:{clr};">{it['Verdict']}</div></div>""", unsafe_allow_html=True)
            with k3:
                st.markdown(f"""<div class="metric-card"><div class="score-label">ENERGÍA (MOMENTUM)</div><div style="margin-top:10px;">{tags_tac if tags_tac else "Sin señales fuertes"}</div><div class="sub-info" style="margin-top:5px;">RVOL: {it['RVOL']:.1f}x | ADX: {it['ADX']:.0f}</div></div>""", unsafe_allow_html=True)
            with k4:
                st.markdown(f"""<div class="metric-card"><div class="score-label">ESTRUCTURA</div><div class="big-score" style="color:#555;">{it['S_Opt']:.1f}</div><div class="sub-info">{it['Sentiment']}</div></div>""", unsafe_allow_html=True)

            # GRÁFICO CON BANDAS
            h = it['History']
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name='Precio')])
            
            # Agregar Bandas Bollinger (Visualmente útil para el Squeeze)
            sma = h['Close'].rolling(20).mean()
            std = h['Close'].rolling(20).std()
            upper = sma + (2*std)
            lower = sma - (2*std)
            
            fig.add_trace(go.Scatter(x=h.index, y=upper, line=dict(color='gray', width=1), name='BB Upper'))
            fig.add_trace(go.Scatter(x=h.index, y=lower, line=dict(color='gray', width=1), name='BB Lower', fill='tonexty', fillcolor='rgba(128,128,128,0.1)'))
            
            if it['CW'] > 0:
                fig.add_hline(y=it['CW'], line_dash="dash", line_color="red", annotation_text="Call Wall")
                fig.add_hline(y=it['PW'], line_dash="dash", line_color="green", annotation_text="Put Wall")
                
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("🕵️ Auditoría de Señales"):
                st.write(f"**Detalles Técnicos:** {', '.join(it['D_Tec'])}")
                st.write(f"**Señales Tácticas:** {', '.join(it['D_Tac'])}")
                st.write(f"**Gestión Riesgo:** ATR ${it['ATR']:.2f} | Stop Loss sugerido: ${it['Price']-(2*it['ATR']):.2f}")

else: st.info("👈 Escanea para buscar oportunidades.")
