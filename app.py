import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN FINAL + UUID", layout="wide")
st.title("ITOSE Tools - VIN FINAL + UUID")

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

# 🔥 UUID จากบรรทัดเดียวกับ VIN
UUID_REGEX = r'([a-f0-9\-]{36})'

def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else ""

# =========================
# UPLOAD
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if datahub_file:

    df = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)

    rows = []   # 🔥 เปลี่ยนจาก map → list (เพราะ UUID ซ้ำได้)

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
                uuid = extract_uuid(text)   # 🔥 ดึง UUID จาก text เดียวกัน

                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        if not vin:
                            continue

                        device = item.get("deviceId", "")
                        carrier = item.get("carrier", "")
                        sim = map_sim(item.get("simPackage", ""))

                        rows.append({
                            "UUID": uuid,          # 🔥 ใส่ก่อน VIN
                            "VIN": vin,
                            "DeviceID": device,
                            "Carrier": carrier,
                            "SimPackage": sim,
                            "Response Message": response,
                            "StatusCode": status,
                            "Message": msg
                        })

            except:
                continue

    # =========================
    # SUMMARY
    # =========================
    st.markdown("### Summary")
    st.metric("VIN ทั้งหมด", len(rows))

    # =========================
    # TABLE
    # =========================
    if rows:

        df_vin = pd.DataFrame(rows).fillna("")
        df_vin = df_vin.reset_index(drop=True)
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.dataframe(df_vin, use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_FULL')

        output.seek(0)

        st.download_button(
            "Download",
            data=output,
            file_name="vin-full-with-uuid.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN")
