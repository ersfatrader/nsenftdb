import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("📊 NIFTY PRO OI DASHBOARD")

# ===== FETCH DATA =====
def get_data():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {"User-Agent": "Mozilla/5.0"}

    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    data = session.get(url, headers=headers).json()

    records = data['records']['data']
    spot = data['records']['underlyingValue']

    rows = []
    for item in records:
        strike = item['strikePrice']
        ce = item.get('CE', {})
        pe = item.get('PE', {})

        rows.append({
            "Strike": strike,
            "CE_OI": ce.get('openInterest', 0),
            "PE_OI": pe.get('openInterest', 0),
            "CE_Chg": ce.get('changeinOpenInterest', 0),
            "PE_Chg": pe.get('changeinOpenInterest', 0)
        })

    return pd.DataFrame(rows), spot

df, spot = get_data()

# ===== BASIC METRICS =====
pcr = df["PE_OI"].sum() / df["CE_OI"].sum()
support = df.loc[df["PE_OI"].idxmax(), "Strike"]
resistance = df.loc[df["CE_OI"].idxmax(), "Strike"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Spot", round(spot,2))
col2.metric("PCR", round(pcr,2))
col3.metric("Support", support)
col4.metric("Resistance", resistance)

# ===== ROUND LEVEL TABLE =====
st.subheader("🎯 Round Level Decision Table")

levels = []

base = int(round(spot / 100) * 100)

for i in range(-3, 4):
    levels.append(base + i*100)
    levels.append(base + i*100 + 50)

levels = sorted(set(levels))

table = []

for lvl in levels:
    nearest = df.iloc[(df['Strike'] - lvl).abs().argsort()[:1]]

    ce_chg = nearest["CE_Chg"].values[0]
    pe_chg = nearest["PE_Chg"].values[0]

    pos = "Near"

    # Interpretation Logic
    if lvl >= spot:  # Resistance side
        if ce_chg > 0 and pe_chg < 0:
            meaning = "🔴 Resistance strengthening → reversal likely"
        elif ce_chg < 0 and pe_chg > 0:
            meaning = "🚀 Resistance weakening → breakout possible"
        else:
            meaning = "⚖️ Mixed signals"
    else:  # Support side
        if pe_chg > 0 and ce_chg < 0:
            meaning = "🟢 Support strengthening → bounce likely"
        elif pe_chg < 0:
            meaning = "💣 Support weakening → breakdown risk"
        else:
            meaning = "⚖️ Mixed signals"

    table.append({
        "Level": lvl,
        "CE Change": ce_chg,
        "PE Change": pe_chg,
        "Interpretation": meaning
    })

table_df = pd.DataFrame(table)
st.dataframe(table_df, use_container_width=True)

# ===== TRAP SIGNAL =====
st.subheader("🧠 Trap Signal")

if pcr > 1.2 and spot < resistance:
    st.error("🔴 Bull Trap Possible")
elif pcr < 0.8 and spot > support:
    st.success("🟢 Bear Trap Possible")
else:
    st.info("No clear trap")
