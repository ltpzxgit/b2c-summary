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

UUID_REGEX = r'([a-f0-9\-]{36})'

def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else ""

# =========================
# UPLOAD
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])
tcap_file = st.file_uploader("TCAPLinkage", type=["xlsx", "csv"])

# =========================
# PROCESS FUNCTION
# =========================
def process_file(df, filter_empty_response=False):
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

                # 🔥 ถ้าเป็น TCAPLinkage แล้ว response ว่าง → skip ทั้ง VIN
                if filter_empty_response and response == "":
                    continue

                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        if not vin:
                            continue

                        device = item.get("deviceId", "")

                        rows.append({
                            "UUID": uuid,
                            "VIN": vin,
                            "DeviceID": device,
                            "Response Message": response,
                            "StatusCode": status
                        })

            except:
                continue

    return rows

# =========================
# RUN
# =========================
if datahub_file or tcap_file:

    all_rows = []

    # -------------------------
    # FILE 1: Datahub (เหมือนเดิม)
    # -------------------------
    if datahub_file:
        df1 = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)
        rows1 = process_file(df1, filter_empty_response=False)
        all_rows.extend(rows1)

    # -------------------------
    # FILE 2: TCAPLinkage (มี filter)
    # -------------------------
    if tcap_file:
        df2 = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)
        rows2 = process_file(df2, filter_empty_response=True)
        all_rows.extend(rows2)

    # =========================
    # SUMMARY
    # =========================
    st.markdown("### Summary")
    st.metric("VIN ทั้งหมด", len(all_rows))

    # =========================
    # TABLE
    # =========================
    if all_rows:

        df_vin = pd.DataFrame(all_rows).fillna("")
        df_vin = df_vin.reset_index(drop=True)
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.dataframe(df_vin, use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_FINAL')

        output.seek(0)

        st.download_button(
            "Download",
            data=output,
            file_name="vin-final-with-uuid.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN")
