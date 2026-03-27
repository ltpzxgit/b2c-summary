import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - Datahub Clean", layout="wide")
st.title("TCAPLinkageDatahub → Clean Columns")

# =========================
# REGEX (ปรับให้ทนขึ้น)
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'
PAIR_REGEX = r'LDCMID":"([^"]+)".*?StatusReg":"([^"]+)".*?ResDate":"([^"]+)"'
VIN_REGEX = r'"vin":"([^"]+)"'
SIM_REGEX = r'"simPackage":"([^"]+)"'

# =========================
# FUNCTIONS
# =========================
def get_carrier(deviceid):
    if isinstance(deviceid, str) and deviceid.startswith(("A", "Z")):
        return "AIS"
    return "TRUE"

def extract_all(text):
    uuid = re.search(UUID_REGEX, text)
    vin = re.search(VIN_REGEX, text)
    sim = re.search(SIM_REGEX, text)

    pairs = re.findall(PAIR_REGEX, text)

    results = []
    for d, s, dt in pairs:
        results.append({
            "UUID": uuid.group(1) if uuid else None,
            "VIN": vin.group(1) if vin else None,
            "DeviceID": d,
            "Result": s,
            "Date": dt,
            "SimPackage": sim.group(1) if sim else None
        })

    return results

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    rows = []

    # =========================
    # PARSE LOG
    # =========================
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val): 
                continue

            text = str(val)
            extracted = extract_all(text)

            for r in extracted:
                r["Carrier"] = get_carrier(r["DeviceID"])
                rows.append(r)

    # =========================
    # HANDLE EMPTY
    # =========================
    if not rows:
        st.error("❌ No data extracted → regex ไม่ match log")
        st.stop()

    df_clean = pd.DataFrame(rows)

    # =========================
    # SAFE DATE
    # =========================
    if "Date" in df_clean.columns:
        df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")
    else:
        st.error("❌ No Date column")
        st.stop()

    # =========================
    # DROP VIN NULL ก่อน
    # =========================
    df_clean = df_clean.dropna(subset=["VIN"])

    # =========================
    # VIN ซ้ำ → เอาล่าสุด
    # =========================
    df_clean = df_clean.sort_values("Date").drop_duplicates(subset=["VIN"], keep="last")

    # =========================
    # CLEAN RESULT
    # =========================
    df_clean["Result"] = df_clean["Result"].astype(str).str.strip()

    # =========================
    # SELECT COLUMNS
    # =========================
    df_clean = df_clean[[
        "UUID",
        "VIN",
        "DeviceID",
        "Carrier",
        "SimPackage",
        "Result"
    ]]

    df_clean = df_clean.reset_index(drop=True)
    df_clean.insert(0, "No.", df_clean.index + 1)

    # =========================
    # SHOW
    # =========================
    st.dataframe(df_clean)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    df_clean.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Download Clean Data",
        data=output,
        file_name="datahub_clean.xlsx"
    )
