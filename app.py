import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - Datahub Clean", layout="wide")
st.title("TCAPLinkageDatahub → Clean Columns")

# =========================
# REGEX
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'   # มี group แล้ว
VIN_REGEX = r'"[Vv][Ii][Nn]":"([^"]+)"'
SIM_REGEX = r'"simPackage":"([^"]+)"'

# =========================
# SAFE GET VALUE (กัน IndexError)
# =========================
def get_value(pattern, text):
    m = re.search(pattern, text)
    if not m:
        return None
    return m.group(1) if m.lastindex else m.group(0)

# =========================
# FUNCTIONS
# =========================
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

    # ดึงแยก field (ทน format เพี้ยน)
    device_ids = re.findall(r'LDCMID":"([^"]+)"', text)
    result_list = re.findall(r'StatusReg":"([^"]+)"', text)
    date_list = re.findall(r'ResDate":"([^"]+)"', text)

    # จับคู่แบบ safe
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

    # =========================
    # PARSE
    # =========================
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            try:
                extracted = extract_rows(text)
                for r in extracted:
                    r["Carrier"] = get_carrier(r["DeviceID"])
                    rows.append(r)
            except:
                continue

    # =========================
    # EMPTY CHECK
    # =========================
    if not rows:
        st.error("❌ No data extracted → format log ไม่ตรง")
        st.write("🔍 Sample:")
        st.code(str(df.iloc[0,0])[:500])
        st.stop()

    df_clean = pd.DataFrame(rows)

    # =========================
    # DATE SAFE
    # =========================
    if "Date" in df_clean.columns:
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
