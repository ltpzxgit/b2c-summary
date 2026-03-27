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

# 🔥 ดึง JSON ARRAY (ข้อมูล VIN)
def extract_json_array(text):
    matches = re.findall(r'\[.*?\]', text)
    for m in matches:
        try:
            data = json.loads(m)
            if isinstance(data, list):
                return data
        except:
            continue
    return None


# 🔥 ดึง JSON OBJECT (status / message)
def extract_tail(text):
    response = ""
    status = ""
    message = ""

    matches = re.findall(r'\{[^{}]*\}', text)

    for m in matches:
        try:
            obj = json.loads(m)

            if isinstance(obj, dict):
                if "message" in obj and response == "":
                    response = obj.get("message", "")

                if "statusCode" in obj and status == "":
                    status = str(obj.get("statusCode", ""))

        except:
            continue

    if "Process" in response:
        message = response

    return response, status, message


UUID_REGEX = r'([a-f0-9\-]{36})'

def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else ""


def map_sim(sim):
    if sim == "C":
        return "Commercial"
    elif sim == "R":
        return "Registration"
    return sim or ""


# =========================
# PROCESS FUNCTION
# =========================
def process_file(df, mode="datahub"):
    rows = []

    for col in df.columns:
        for val in df[col]:

            if pd.isna(val):
                continue

            text = str(val)

            data = extract_json_array(text)
            if not data:
                continue

            response, status, msg = extract_tail(text)
            uuid = extract_uuid(text)

            # 🔥 TCAP filter (มี response เท่านั้น)
            if mode == "tcap" and response == "":
                continue

            for item in data:

                vin = item.get("vin", "")
                if not vin:
                    continue

                device = item.get("deviceId", "")
                carrier = item.get("carrier", "")
                sim = map_sim(item.get("simPackage", ""))

                if mode == "datahub":
                    rows.append({
                        "UUID": uuid,
                        "VIN": vin,
                        "DeviceID": device,
                        "Carrier": carrier,
                        "SimPackage": sim,
                        "Response Message": response,
                        "StatusCode": status,
                        "Message": msg
                    })

                elif mode == "tcap":
                    rows.append({
                        "UUID": uuid,
                        "VIN": vin,
                        "DeviceID": device,
                        "Response Message": response,
                        "StatusCode": status
                    })

    return rows


# =========================
# UPLOAD
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])
tcap_file = st.file_uploader("TCAPLinkage", type=["xlsx", "csv"])

# =========================
# RUN
# =========================
rows1 = []
rows2 = []

if datahub_file:
    df1 = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)
    rows1 = process_file(df1, mode="datahub")

if tcap_file:
    df2 = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)
    rows2 = process_file(df2, mode="tcap")

# =========================
# SUMMARY
# =========================
if datahub_file or tcap_file:
    st.markdown("### Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Datahub VIN", len(rows1))
    col2.metric("TCAP VIN", len(rows2))
    col3.metric("Total VIN", len(rows1) + len(rows2))

# =========================
# DISPLAY
# =========================
if rows1 or rows2:

    df1_display = pd.DataFrame(rows1).fillna("")
    df2_display = pd.DataFrame(rows2).fillna("")

    # -------- Sheet 1 --------
    if not df1_display.empty:
        df1_display = df1_display.reset_index(drop=True)
        df1_display.insert(0, "No.", df1_display.index + 1)

        st.markdown(f"### TCAPLinkageDatahub ({len(df1_display)} VIN)")
        st.dataframe(df1_display, use_container_width=True)
    else:
        st.warning("⚠️ TCAPLinkageDatahub ไม่มีข้อมูล")

    # -------- Sheet 2 --------
    if not df2_display.empty:
        df2_display = df2_display.reset_index(drop=True)
        df2_display.insert(0, "No.", df2_display.index + 1)

        st.markdown(f"### TCAPLinkage ({len(df2_display)} VIN)")
        st.dataframe(df2_display, use_container_width=True)
    else:
        st.warning("⚠️ TCAPLinkage ไม่มีข้อมูล")

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        if not df1_display.empty:
            df1_display.to_excel(writer, index=False, sheet_name='TCAPLinkageDatahub')

        if not df2_display.empty:
            df2_display.to_excel(writer, index=False, sheet_name='TCAPLinkage')

    output.seek(0)

    st.download_button(
        "📥 Download Excel (2 Sheets)",
        data=output,
        file_name="vin-separated-sheets.xlsx"
    )

else:
    if datahub_file or tcap_file:
        st.error("❌ ไม่เจอ VIN")
