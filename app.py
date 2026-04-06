import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C", layout="wide")
st.title("ITOSE Tools - B2C Summary")

# =========================
# CSS (FDF STYLE)
# =========================
st.markdown("""
<style>
.card {
    padding: 20px;
    border-radius: 14px;
    background: linear-gradient(145deg, #0f172a, #111827);
    border: 1px solid #374151;
    text-align: center;
}
.card-red {
    padding: 20px;
    border-radius: 14px;
    background: linear-gradient(145deg, #2a0f0f, #1a0f0f);
    border: 1px solid #7f1d1d;
    text-align: center;
}
.card-title {
    font-size: 14px;
    color: #9ca3af;
}
.card-value {
    font-size: 42px;
    font-weight: bold;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CARD
# =========================
def card(title, value, is_red=False):
    cls = "card-red" if is_red else "card"
    return f"""
    <div class="{cls}">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """

# =========================
# COMMON FUNCTIONS
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
# FILE 3
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
# UPLOAD
# =========================
c1, c2, c3 = st.columns(3)

with c1:
    file1 = st.file_uploader("TCAPLinkageDatahub")
with c2:
    file2 = st.file_uploader("TCAPLinkage")
with c3:
    file3 = st.file_uploader("VehicleSettingRequester")

# =========================
# PROCESS
# =========================
if file1:

    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    df_vin1 = pd.DataFrame(process_file(df1)).fillna("")
    df_vin1.insert(0, "No.", range(1, len(df_vin1)+1))

    df_vin2 = pd.DataFrame()
    df_vin3 = pd.DataFrame()
    df_error = pd.DataFrame()

    if file2:
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
        df_vin2 = pd.DataFrame(process_file_v2(df2)).fillna("")
        df_vin2.insert(0, "No.", range(1, len(df_vin2)+1))

    if file3:
        df3 = pd.read_csv(file3) if file3.name.endswith(".csv") else pd.read_excel(file3)
        df_vin3 = parse_vehicle_setting(df3)

    # =========================
    # ERROR LOGIC (🔥 สำคัญ)
    # =========================
    if not df_vin1.empty and not df_vin3.empty:

        vins_1 = set(df_vin1["VIN"].dropna())
        vins_3 = set(df_vin3["VIN"].dropna())

        error_vins = vins_1 - vins_3

        if error_vins:
            df_error = df_vin1[df_vin1["VIN"].isin(error_vins)].copy()

            df_error = df_error.iloc[::-1]\
                .drop_duplicates(subset=["VIN"], keep="first")\
                .iloc[::-1]\
                .reset_index(drop=True)

            df_error.insert(0, "No.", range(1, len(df_error)+1))

    # =========================
    # SUMMARY
    # =========================
    st.markdown("## Summary")

    r1 = st.columns(3)
    r2 = st.columns(1)

    with r1[0]:
        st.markdown(card("TCAPLinkageDatahub", len(df_vin1)), unsafe_allow_html=True)
    with r1[1]:
        st.markdown(card("TCAPLinkage", len(df_vin2)), unsafe_allow_html=True)
    with r1[2]:
        st.markdown(card("VehicleSettingRequester", len(df_vin3)), unsafe_allow_html=True)

    with r2[0]:
        st.markdown(card("Error", len(df_error), True), unsafe_allow_html=True)

    st.divider()

    # =========================
    # TABLE
    # =========================
    st.subheader("TCAPLinkageDatahub")
    st.dataframe(df_vin1, use_container_width=True)

    if not df_vin2.empty:
        st.subheader("TCAPLinkage")
        st.dataframe(df_vin2, use_container_width=True)

    if not df_vin3.empty:
        st.subheader("VehicleSettingRequester")
        st.dataframe(df_vin3, use_container_width=True)

    if not df_error.empty:
        st.subheader("Error")
        st.dataframe(df_error, use_container_width=True)

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

        if not df_error.empty:
            df_error.to_excel(writer, index=False, sheet_name='Error')

    output.seek(0)

    st.download_button(
        "Download",
        data=output,
        file_name="b2c-summary.xlsx"
    )

else:
    st.info("Please upload 1st file first")
