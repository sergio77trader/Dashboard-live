import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, datetime
from scipy import optimize

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Bonos USD Auto")

# --- MOTORES DE DATOS ---
# Mapeo: Nombre en pantalla -> Ticker en Yahoo Finance
TICKER_MAP = {
    "AL30 (Ley Arg 2030)": "AL30D.BA",
    "GD30 (Ley NY 2030)": "GD30D.BA",
    "AL29 (Ley Arg 2029)": "AL29D.BA",
    "GD29 (Ley NY 2029)": "GD29D.BA",
    "AL35 (Ley Arg 2035)": "AL35D.BA",
    "GD35 (Ley NY 2035)": "GD35D.BA"
}

# Flujos de Fondos APROXIMADOS (Prospecto 2020 base 100 VN)
# Nota: Simplificado para cálculo de TIR rápida.
CASHFLOWS = {
    "AL30 (Ley Arg 2030)": [
        {"fecha": date(2025, 7, 9), "interes": 0.38, "capital": 4.00},
        {"fecha": date(2026, 1, 9), "interes": 0.36, "capital": 4.00},
        {"fecha": date(2026, 7, 9), "interes": 0.34, "capital": 4.00},
        {"fecha": date(2027, 1, 9), "interes": 0.32, "capital": 4.00},
        {"fecha": date(2027, 7, 9), "interes": 0.30, "capital": 8.00},
        {"fecha": date(2028, 1, 9), "interes": 0.26, "capital": 8.00},
        {"fecha": date(2028, 7, 9), "interes": 0.22, "capital": 8.00},
        {"fecha": date(2029, 1, 9), "interes": 0.18, "capital": 8.00},
        {"fecha": date(2029, 7, 9), "interes": 0.14, "capital": 8.00},
        {"fecha": date(2030, 1, 9), "interes": 0.10, "capital": 8.00},
        {"fecha": date(2030, 7, 9), "interes": 0.06, "capital": 24.00}
    ],
    # GD30 tiene el mismo flujo que AL30, solo cambia la legislación
    "GD30 (Ley NY 2030)": [
        {"fecha": date(2025, 7, 9), "interes": 0.38, "capital": 4.00},
        {"fecha": date(2026, 1, 9), "interes": 0.36, "capital": 4.00},
        {"fecha": date(2026, 7, 9), "interes": 0.34, "capital": 4.00},
        {"fecha": date(2027, 1, 9), "interes": 0.32, "capital": 4.00},
        {"fecha": date(2027, 7, 9), "interes": 0.30, "capital": 8.00},
        {"fecha": date(2028, 1, 9), "interes": 0.26, "capital": 8.00},
        {"fecha": date(2028, 7, 9), "interes": 0.22, "capital": 8.00},
        {"fecha": date(2029, 1, 9), "interes": 0.18, "capital": 8.00},
        {"fecha": date(2029, 7, 9), "interes": 0.14, "capital": 8.00},
        {"fecha": date(2030, 1, 9), "interes": 0.10, "capital": 8.00},
        {"fecha": date(2030, 7, 9), "interes": 0.06, "capital": 24.00}
    ]
    # Se pueden agregar AL29/35 replicando la lógica
}

def get_live_price(ticker_yahoo):
    """Intenta obtener el precio en tiempo real de Yahoo"""
    try:
        info = yf.Ticker(ticker_yahoo).fast_info
        if info.last_price:
            return float(info.last_price)
    except:
        pass
    return None

def xirr(cashflows, dates):
    """Calcula TIR (Tasa Interna de Retorno)"""
    def npv(rate):
        total_value = 0.0
        t0 = dates[0]
        for i, cf in enumerate(cashflows):
            d = (dates[i] - t0).days
            total_value += cf / ((1 + rate) ** (d / 365.0))
        return total_value
    try:
        return optimize.newton(npv, 0.20)
    except:
        return None

# --- INTERFAZ ---
st.title("🏛️ Calculadora Bonos USD (Auto-Price)")
st.caption("Conexión: Yahoo Finance (Dólar MEP/Cable Implícito)")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Configuración")
    bono_key = st.selectbox("Elegir Bono:", list(CASHFLOWS.keys()))
    
    # 1. INTENTO DE AUTODETECTAR PRECIO
    ticker_yf = TICKER_MAP.get(bono_key, "")
    precio_detectado = get_live_price(ticker_yf)
    
    val_inicial = 60.0
    label_precio = "Precio Manual:"
    
    if precio_detectado:
        val_inicial = precio_detectado
        st.success(f"✅ Precio detectado: ${precio_detectado:.2f}")
        label_precio = "Precio (Editable):"
    else:
        st.warning("⚠️ No se detectó precio online. Ingrese manual.")
    
    # Input numérico (se pre-llena si hay dato)
    precio = st.number_input(label_precio, value=val_inicial, step=0.1, format="%.2f")
    comision = st.number_input("Comisión (%)", value=0.5, step=0.1) / 100
    
    if st.button("CALCULAR RENDIMIENTO", type="primary"):
        st.session_state['calc_done'] = True

with col2:
    if st.session_state.get('calc_done', False):
        flujo = CASHFLOWS[bono_key]
        
        # Armado de Cashflow para XIRR
        inversion = -precio * (1 + comision)
        fechas = [date.today()]
        montos = [inversion]
        
        tabla_pagos = []
        total_cobrar = 0
        
        for p in flujo:
            if p["fecha"] > date.today():
                total_pago = p["interes"] + p["capital"]
                fechas.append(p["fecha"])
                montos.append(total_pago)
                total_cobrar += total_pago
                
                tabla_pagos.append({
                    "Fecha": p["fecha"],
                    "Interés": p["interes"],
                    "Amortización": p["capital"],
                    "Total": total_pago
                })
        
        tir = xirr(montos, fechas)
        
        # Paridad Técnica (Aprox 96 USD residual)
        paridad = (precio / 96.00) * 100 
        
        # --- TARJETAS DE RESULTADOS ---
        st.subheader("Resultados del Análisis")
        k1, k2, k3 = st.columns(3)
        
        k1.metric("TIR (Anual en USD)", f"{tir:.2%}", delta="Yield")
        k2.metric("Paridad", f"{paridad:.2f}%", help="Bajo 100% = Con Descuento")
        k3.metric("Retorno Total", f"x{(total_cobrar/abs(inversion)):.2f}", help="Multiplicador de capital")
        
        st.divider()
        st.write("📅 **Calendario de Cobros (USD Billete):**")
        st.dataframe(pd.DataFrame(tabla_pagos), use_container_width=True)

    else:
        st.info("👈 Confirma el precio y presiona Calcular.")
