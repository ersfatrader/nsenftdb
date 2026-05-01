import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(layout="wide")
st.title("📊 NIFTY PRO OI DASHBOARD")

# =========================
# FETCH DATA (FIXED NSE)
# =========================
def get_data():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/option-chain"
    }

    session = requests.Session()

    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)

        if response.status_code != 200:
            return pd.DataFrame(), 0

        data = response.json()

        if "records" not in data or "data" not in data["records"]:
            return pd.DataFrame(), 0

        records = data["records"]["data"]
        spot = data["records"].get("underlyingValue", 0)

        rows = []

        for item in records:
            strike = item["strikePrice"]

            ce = item.get("CE", {})
            pe = item.get("PE", {})

            rows.append({
                "Strike": strike,
                "CE_OI": ce.get("openInterest", 0),
                "PE_OI": pe.get("openInterest", 0),
                "CE_Chg": ce.get("changeinOpenInterest", 0),
                "PE_Chg": pe.get("changeinOpenInterest", 0)
            })

        df = pd.DataFrame(rows)

        return df, spot

    except:
        return pd.DataFrame(), 0


df, spot = get_data()

# =========================
# HANDLE BLOCK
# =========================
if df.empty:
    st.error("⚠️ NSE blocked request. Refresh after few seconds.")
    st.stop()

# =========================
# BASIC METRICS
# =========================
total_ce = df["CE_OI"].sum()
total_pe = df["PE_OI"].sum()
pcr = total_pe / total_ce if total_ce != 0 else 0

support = df.loc[df["PE_OI"].idxmax(), "Strike"]
resistance = df.loc[df["CE_OI"].idxmax(), "Strike"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("📍 Spot", round(spot, 2))
col2.metric("📊 PCR", round(pcr, 2))
col3.metric("🟢 Support", support)
col4.metric("🔴 Resistance", resistance)

# =========================
# PCR INTERPRETATION
# =========================
if pcr > 1.2:
    st.warning("⚠️ Bullish Crowd → Possible Bull Trap")
elif pcr < 0.8:
    st.warning("⚠️ Bearish Crowd → Possible Bear Trap")
else:
    st.info("⚖️ Balanced Market")

# =========================
# ROUND LEVEL TABLE
# =========================
st.subheader("🎯 Round Level Decision Table")

levels = []

base = int(round(spot / 100) * 100)

for i in range(-3, 4):
    levels.append(base + i * 100)
    levels.append(base + i * 100 + 50)

levels = sorted(set(levels))

table = []

for lvl in levels:

    nearest = df.iloc[(df['Strike'] - lvl).abs().argsort()[:1]]

    ce_chg = nearest["CE_Chg"].values[0]
    pe_chg = nearest["PE_Chg"].values[0]

    distance = abs(spot - lvl)

    if distance > 150:
        continue

    # ===== INTERPRETATION =====
    if lvl >= spot:  # Resistance zone

        if ce_chg > 0 and pe_chg < 0:
            meaning = "🔴 Resistance strengthening → Reversal likely"
        elif ce_chg < 0 and pe_chg > 0:
            meaning = "🚀 Resistance weakening → Breakout possible"
        elif ce_chg > 0 and pe_chg > 0:
            meaning = "⚠️ Both sides active → Volatility possible"
        else:
            meaning = "⚖️ Mixed signals"

    else:  # Support zone

        if pe_chg > 0 and ce_chg < 0:
            meaning = "🟢 Support strengthening → Bounce likely"
        elif pe_chg < 0:
            meaning = "💣 Support weakening → Breakdown risk"
        elif pe_chg > 0 and ce_chg > 0:
            meaning = "⚠️ Both sides active → Range zone"
        else:
            meaning = "⚖️ Mixed signals"

    table.append({
        "Level": lvl,
        "Distance": round(distance),
        "CE Change": ce_chg,
        "PE Change": pe_chg,
        "Interpretation": meaning
    })

table_df = pd.DataFrame(table).sort_values("Distance")

st.dataframe(table_df, use_container_width=True)

# =========================
# TRAP SIGNAL
# =========================
st.subheader("🧠 Trap Signal")

if pcr > 1.2 and spot < resistance:
    st.error("🔴 Bull Trap Possible (Watch for breakdown)")
elif pcr < 0.8 and spot > support:
    st.success("🟢 Bear Trap Possible (Watch for breakout)")
else:
    st.info("No strong trap detected")

# =========================
# OI CHART
# =========================
st.subheader("📊 OI Distribution")

chart_df = df.set_index("Strike")[["CE_OI", "PE_OI"]]
st.line_chart(chart_df)

# =========================
# AUTO REFRESH
# =========================
time.sleep(30)
st.rerun()
