import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - Datahub Clean", layout="wide")
st.title("TCAPLinkageDatahub → Clean Columns")

# =========================
# REGEX (FIX จาก log จริง)
# =========================
UUID_REGEX = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'
VIN_REGEX = r'"[Vv][Ii][Nn]":"([^"]+)"'
SIM_REGEX = r'"simPackage":"([^"]+)"'

# =========================
# FUNCTIONS
# =========================
def get_value(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None

def get_carrier(deviceid):
    if isinstance(deviceid, str) and deviceid.startswith(("A", "Z")):
        return "AIS"
    return "TRUE"

def clean_result(text):
    if not text:
        return None
    if "success" in text.lower():
        return "Operation Success"
    return text.strip()

def extract_rows(text):
    results = []

    uuid = get_value(UUID_REGEX, text)
    vin = get_value(VIN_REGEX, text)
    sim = get_value(SIM_REGEX, text) or "Unknown"

    # 👉 ดึง field แยก
    device_ids = re.findall(r'LDCMID":"([^"]+)"', text)
    result_list = re.findall(r'StatusReg":"([^"]+)"', text)
    date_list = re.findall(r'ResDate":"([^"]+)"', text)

    length = min(len(device_ids), len(result_list), len(date_list))

    for i in range(length):
        results.append({
            "UUID": uuid,
            "VIN": vin,
            "DeviceID": device_ids[i],
            "Result": clean_result(result_list[i]),
            "Date": date_list[i],
            "SimPackage": sim
        })

    return results

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    rows = []

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            extracted = extract_rows(text)

            for r in extracted:
                r["Carrier"] = get_carrier(r["DeviceID"])
                rows.append(r)

    if not rows:
        st.error("❌ ยัง parse ไม่ได้ → log ไม่มี LDCMID/StatusReg/ResDate")
        st.code(str(df.iloc[0,0])[:500])
        st.stop()

    df_clean = pd.DataFrame(rows)

    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")

    df_clean = df_clean.dropna(subset=["VIN"])

    df_clean = df_clean.sort_values("Date").drop_duplicates(subset=["VIN"], keep="last")

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

    st.dataframe(df_clean, use_container_width=True)

    output = BytesIO()
    df_clean.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Download Clean Data",
        data=output,
        file_name="datahub_clean.xlsx"
    )
