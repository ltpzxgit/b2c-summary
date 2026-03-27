import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - Datahub Clean", layout="wide")
st.title("TCAPLinkageDatahub → Clean Columns")

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

    # 👉 ดึงค่าแบบแยก (ไม่พัง)
    uuid = get_value(r'[a-f0-9\-]{36}', text)
    vin = get_value(r'"[Vv][Ii][Nn]":"([^"]+)"', text)
    sim = get_value(r'"simPackage":"([^"]+)"', text) or "Unknown"

    # 👉 หา DeviceID ทั้งหมด
    device_ids = re.findall(r'LDCMID":"([^"]+)"', text)

    # 👉 หา Result ทั้งหมด
    results_list = re.findall(r'StatusReg":"([^"]+)"', text)

    # 👉 หา Date ทั้งหมด
    dates = re.findall(r'ResDate":"([^"]+)"', text)

    # 👉 จับคู่ตาม index
    for i in range(min(len(device_ids), len(results_list), len(dates))):
        results.append({
            "UUID": uuid,
            "VIN": vin,
            "DeviceID": device_ids[i],
            "Result": clean_result(results_list[i]),
            "Date": dates[i],
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

    # =========================
    # PARSE
    # =========================
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            extracted = extract_rows(text)
            for r in extracted:
                r["Carrier"] = get_carrier(r["DeviceID"])
                rows.append(r)

    # =========================
    # CHECK
    # =========================
    if not rows:
        st.error("❌ ยัง extract ไม่ได้ → log format แปลกกว่าที่คิด")
        
        # 👉 debug โชว์ sample จริง
        st.write("🔍 Sample log:")
        st.code(str(df.iloc[0,0])[:500])
        
        st.stop()

    df_clean = pd.DataFrame(rows)

    # =========================
    # DATE
    # =========================
    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")

    # =========================
    # CLEAN
    # =========================
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

    # =========================
    # SHOW
    # =========================
    st.dataframe(df_clean, use_container_width=True)

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
