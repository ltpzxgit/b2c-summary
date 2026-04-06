import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C", layout="wide")
st.title("ITOSE Tools - B2C Summary")

# =========================
# UI STYLE
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

[data-testid="stFileUploader"] > div {
    padding: 8px !important;
}
[data-testid="stFileUploader"] section {
    padding: 14px !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] p {
    font-size: 14px !important;
}
[data-testid="stFileUploader"] button {
    padding: 6px 12px !important;
    font-size: 13px !important;
}
[data-testid="stFileUploader"] {
    margin-bottom: 10px !important;
}
[data-testid="stFileUploader"] section div {
    gap: 6px !important;
}

.summary-card {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid #334155;
}

.summary-title {
    color: #94a3b8;
    font-size: 16px;
}

.summary-number {
    color: white;
    font-size: 48px;
    font-weight: 700;
    margin: 10px 0;
}

.summary-error {
    margin-top: 10px;
    padding: 10px;
    border-radius: 12px;
    border: 1px solid #22c55e;
    color: #22c55e;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNCTIONS
# =========================
def extract_json(text):
    match = re.search(r'(\[.*\])', text)
    return match.group(1) if match else None

def map_sim(sim):
    return "Commercial" if sim == "C" else "Registration" if sim == "R" else sim or ""

def extract_tail(text):
    response, status, message = "", "", ""
    text = text.replace('""', '"')

    m_status = re.search(r'"statusCode"\s*:\s*"?(\d+)"?', text)
    if m_status:
        status = m_status.group(1)

    m_response = re.search(r'"message"\s*:\s*"([^"]+)"', text)
    if m_response:
        response = m_response.group(1)

    if "Process" in response:
        message = response

    return response, status, message

UUID_REGEX = r'([a-f0-9\-]{36})'
def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else ""

# =========================
# FILE 1
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
# FILE 2
# =========================
def process_file_v2(df):
    rows = []
    response_map = {}

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            uuid = extract_uuid(text)

            if "response body" in text:
                response, status, msg = extract_tail(text)
                if uuid:
                    response_map[uuid] = (response, status, msg)

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            uuid = extract_uuid(text)
            json_str = extract_json(text)
            if not json_str:
                continue

            try:
                data = json.loads(json_str)
                response, status, msg = response_map.get(uuid, ("", "", ""))

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
# FILE 3 (🔥 เพิ่มใหม่)
# =========================
def extract_body_data(text):
    if "body={" not in text:
        return {}
    try:
        part = text.split("body={", 1)[1].split("}", 1)[0]
        data = {}
        for item in part.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                data[k.strip()] = v.strip()
        return data
    except:
        return {}

def extract_response_data(text):
    if "Response:" not in text:
        return {}
    try:
        part = text.split("Response:", 1)[1]
        start = part.find("{")
        end = part.rfind("}") + 1
        clean = part[start:end].replace('""', '"')
        data = json.loads(clean)
        return {
            "StatusCode": data.get("statusCode"),
            "ResponseMessage": data.get("message")
        }
    except:
        return {}

def parse_vehicle_setting(df):
    logs = []
    for col in df.columns:
        logs.extend(df[col].dropna().astype(str).tolist())

    uuid_map = {}

    for text in logs:
        uuid = extract_uuid(text)
        if not uuid:
            continue

        uuid_map.setdefault(uuid, {})

        if "Request:" in text:
            uuid_map[uuid].update(extract_body_data(text))

        if "Response:" in text:
            uuid_map[uuid].update(extract_response_data(text))

    rows = []
    for i, (uuid, data) in enumerate(uuid_map.items(), start=1):
        rows.append({
            "No.": i,
            "UUID": uuid,
            "VIN": data.get("vin"),
            "DeviceID": data.get("deviceId"),
            "IMEI": data.get("IMEI"),
            "SimStatus": data.get("simStatus"),
            "SimPackage": data.get("simPackage"),
            "StatusCode": data.get("StatusCode"),
            "ResponseMessage": data.get("ResponseMessage"),
        })

    return pd.DataFrame(rows)

# =========================
# UPLOAD (🔥 เพิ่ม file3)
# =========================
col1, col2, col3 = st.columns([1,1,1], gap="large")

with col1:
    st.markdown("TCAPLinkageDatahub")
    file1 = st.file_uploader("", type=["xlsx", "csv"], key="file1")

with col2:
    st.markdown("TCAPLinkage")
    file2 = st.file_uploader("", type=["xlsx", "csv"], key="file2")

with col3:
    st.markdown("VehicleSettingRequester")
    file3 = st.file_uploader("", type=["xlsx", "csv"], key="file3")

# =========================
# PROCESS
# =========================
if file1:

    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    rows1 = process_file(df1)

    df_vin1 = pd.DataFrame(rows1).fillna("")
    df_vin1.insert(0, "No.", range(1, len(df_vin1)+1))

    df_vin2 = pd.DataFrame()
    df_vin3 = pd.DataFrame()

    if file2:
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
        rows2 = process_file_v2(df2)

        df_vin2 = pd.DataFrame(rows2).fillna("")
        df_vin2.insert(0, "No.", range(1, len(df_vin2)+1))

    if file3:
        df3 = pd.read_csv(file3) if file3.name.endswith(".csv") else pd.read_excel(file3)
        df_vin3 = parse_vehicle_setting(df3)

    # =========================
    # SUMMARY
    # =========================
    st.markdown("## Summary")

    cards = []
    cards.append(("TCAPLinkageDatahub", len(df_vin1), 0))

    if not df_vin2.empty:
        cards.append(("TCAPLinkage", len(df_vin2), 0))

    if not df_vin3.empty:
        cards.append(("VehicleSettingRequester", len(df_vin3), 0))

    cols = st.columns(len(cards))

    for i, (title, total, error) in enumerate(cards):
        with cols[i]:
            summary_card(title, total, error)

    # =========================
    # TABLE
    # =========================
    st.markdown("### TCAPLinkageDatahub")
    st.dataframe(df_vin1, use_container_width=True)

    if not df_vin2.empty:
        st.markdown("### TCAPLinkage")
        st.dataframe(df_vin2, use_container_width=True)

    if not df_vin3.empty:
        st.markdown("### VehicleSettingRequester")
        st.dataframe(df_vin3, use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_vin1.to_excel(writer, index=False, sheet_name='TCAPLinkageDataHub')

        if not df_vin2.empty:
            df_vin2.to_excel(writer, index=False, sheet_name='TCAPLinkage')

        if not df_vin3.empty:
            df_vin3.to_excel(writer, index=False, sheet_name='VehicleSettingRequester')

    output.seek(0)

    st.download_button(
        "Download",
        data=output,
        file_name="b2c-summary.xlsx"
    )

else:
    st.info("Please upload 1st file first")
