import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - Datahub Clean", layout="wide")
st.title("TCAPLinkageDatahub → Clean Columns")

# =========================
# FUNCTIONS
# =========================
def get(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None

def get_carrier(deviceid, carrier):
    if carrier:
        return carrier
    if isinstance(deviceid, str) and deviceid.startswith(("A", "Z")):
        return "AIS"
    return "TRUE"

def clean_result(msg):
    if not msg:
        return None
    if "success" in msg.lower():
        return "Operation Success"
    return msg

def extract(text):
    rows = []

    # 👉 ดึงค่าตรงๆจาก JSON
    vin = get(r'"vin":"([^"]+)"', text)
    device = get(r'"deviceId":"([^"]+)"', text)
    carrier = get(r'"carrier":"([^"]+)"', text)
    sim = get(r'"simPackage":"([^"]+)"', text)
    msg = get(r'"message":"([^"]+)"', text)

    # 👉 UUID จาก header log
    uuid = get(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})', text)

    # 👉 Date
    date = get(r'"Sendingtime":"([^"]+)"', text)

    if vin and device:
        rows.append({
            "UUID": uuid,
            "VIN": vin,
            "DeviceID": device,
            "Carrier": get_carrier(device, carrier),
            "SimPackage": sim if sim else "Unknown",
            "Result": clean_result(msg),
            "Date": date
        })

    return rows

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

            try:
                data = extract(text)
                rows.extend(data)
            except:
                continue

    # =========================
    # CHECK
    # =========================
    if not rows:
        st.error("❌ ยัง parse ไม่ได้ → แต่ตอนนี้ structure ถูกแล้ว ต้องเช็ค sample")
        st.code(str(df.iloc[0,0])[:500])
        st.stop()

    df_clean = pd.DataFrame(rows)

    # =========================
    # DATE
    # =========================
    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")

    # =========================
    # VIN ล่าสุด
    # =========================
    df_clean = df_clean.sort_values("Date").drop_duplicates(subset=["VIN"], keep="last")

    # =========================
    # SELECT
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
