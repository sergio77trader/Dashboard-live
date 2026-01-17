import streamlit as st
import pandas as pd
import time
import requests

BASE_URL = "https://api-futures.kucoin.com"

st.set_page_config(page_title="KuCoin Scanner", layout="wide")

st.title("KuCoin Perpetuos - Prueba Base (FUNCIONAL)")

@st.cache_data(ttl=60)
def traer_perpetuos_usdtp_por_lotes(lote_size=50):

    url = f"{BASE_URL}/api/v1/contracts/active"
    r = requests.get(url, timeout=15)
    data = r.json()

    if data.get("code") != "200000":
        st.error("KuCoin no respondió bien. Probá en 30–60 segundos.")
        return pd.DataFrame()

    contracts = data["data"]

    symbols = [c["symbol"] for c in contracts if "USDTM" in c["symbol"]]

    st.write(f"Total contratos USDT-M encontrados: {len(symbols)}")

    dfs = []
    columnas_vistas = set()

    for i in range(0, len(symbols), lote_size):
        lote = symbols[i:i+lote_size]
        st.write(f"Procesando lote {i} → {i+lote_size}")

        filas = []

        for s in lote:
            try:
                ticker_url = f"{BASE_URL}/api/v1/ticker?symbol={s}"
                r = requests.get(ticker_url, timeout=10)
                d = r.json()

                if d.get("code") == "200000":
                    row = d["data"]
                    row["cripto"] = s
                    filas.append(row)

            except Exception as e:
                st.warning(f"Error con {s}: {e}")

        if filas:
            df_lote = pd.DataFrame(filas)
            columnas_vistas.update(df_lote.columns)
            dfs.append(df_lote)

        time.sleep(1.2)

    if not dfs:
        st.error("KuCoin no devolvió datos válidos.")
        return pd.DataFrame()

    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.reindex(columns=list(columnas_vistas))

    if "cripto" in df_final.columns:
        df_final = df_final.sort_values("cripto").reset_index(drop=True)

    return df_final


df = traer_perpetuos_usdtp_por_lotes(lote_size=50)

if df.empty:
    st.stop()

st.subheader("Datos crudos de KuCoin (base funcional)")

st.dataframe(df, use_container_width=True)

st.success("Si ves la tabla arriba, ESTO FUNCIONA y ya tenés la base correcta.")
