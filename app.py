import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C", layout="wide")
st.title("ITOSE Tools - B2C Summary")

# =========================
# FUNCTIONS
# =========================
def extract_json(text):
    match = re.search(r'(\[.*\])', text)
    if match:
        return match.group(1)
    return None

def map_sim(sim):
    if sim == "C":
        return "Commercial"
    elif sim == "R":
        return "Registration"
    return sim or ""

def extract_tail(text):
    response = ""
    status = ""
    message = ""

    m1 = re.search(r'"message"\s*:\s*"([^"]+)"\s*,\s*"statusCode"', text)
    if m1:
        response = m1.group(1)

    m2 = re.search(r'"statusCode"\s*:\s*(\d+)', text)
    if m2:
        status = m2.group(1)

    m3 = re.search(r'"message"\s*:\s*"([^"]+)"', text)
    if m3:
        msg_val = m3.group(1)
        if "Process" in msg_val:
            message = msg_val

    return response, status, message

UUID_REGEX = r'([a-f0-9\-]{36})'

def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else ""

# =========================
# CORE PROCESS (ใช้ร่วมกัน)
# =========================
def process_file(df):
    rows = []

    for col in df.columns:
        for val in df[col]:

            if pd.isna(val):
                continue

            text = str(val)

            json_str = extract_json(text)
            if not json_str:
                continue

            try:
                data = json.loads(json_str)

                response, status, msg = extract_tail(text)
                uuid = extract_uuid(text)

                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        if not vin:
                            continue

                        rows.append({
                            "UUID": uuid,
                            "VIN": vin,
                            "DeviceID": item.get("deviceId", ""),
                            "Carrier": item.get("carrier", ""),
                            "SimPackage": map_sim(item.get("simPackage", "")),
                            "Response Message": response,
                            "StatusCode": status,
                            "Message": msg
                        })

            except:
                continue

    return rows

# =========================
# UPLOAD
# =========================
file1 = st.file_uploader("TCAPLinkageDatahub (ไฟล์ 1)", type=["xlsx", "csv"])
file2 = st.file_uploader("TCAPLinkage (ไฟล์ 2)", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if file1:

    # ===== FILE 1 =====
    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    rows1 = process_file(df1)

    st.markdown("### Summary (File 1)")
    st.metric("VIN ทั้งหมด", len(rows1))

    df_vin1 = pd.DataFrame(rows1).fillna("")
    df_vin1 = df_vin1.reset_index(drop=True)
    df_vin1.insert(0, "No.", df_vin1.index + 1)

    st.dataframe(df_vin1, use_container_width=True)

    # ===== FILE 2 =====
    df_vin2 = pd.DataFrame()

    if file2:
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
        rows2 = process_file(df2)

        st.markdown("### Summary (File 2 - TCAPLinkage)")
        st.metric("VIN ทั้งหมด (TCAP)", len(rows2))

        df_vin2 = pd.DataFrame(rows2).fillna("")
        df_vin2 = df_vin2.reset_index(drop=True)
        df_vin2.insert(0, "No.", df_vin2.index + 1)

        # 🔥 ตัด Carrier / SimPackage / Message ออก
        df_vin2 = df_vin2[[
            "No.",
            "UUID",
            "VIN",
            "DeviceID",
            "Response Message",
            "StatusCode"
        ]]

        st.dataframe(df_vin2, use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_vin1.to_excel(writer, index=False, sheet_name='VIN_FULL')

        if not df_vin2.empty:
            df_vin2.to_excel(writer, index=False, sheet_name='TCAPLinkage')

    output.seek(0)

    st.download_button(
        "Download",
        data=output,
        file_name="b2c-2-sheets.xlsx"
    )

else:
    st.info("กรุณา Upload ไฟล์ 1 ก่อน")
