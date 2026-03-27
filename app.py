import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C AUTO", layout="wide")
st.title("ITOSE Tools - B2C (Auto Detect Mode - 3 Files)")

# =========================
# REGEX
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'
JSON_BLOCK_REGEX = r'\{.*?\}'

# =========================
# FUNCTIONS
# =========================
def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else "-"


def extract_json_blocks(text):
    return re.findall(JSON_BLOCK_REGEX, text)


def try_parse_json(block):
    try:
        block = block.replace('\\"', '"')
        return json.loads(block)
    except:
        return None


def normalize_to_list(data):
    if isinstance(data, list):
        return data, "-", "-"

    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"], data.get("message", "-"), data.get("statusCode", "-")
        else:
            return [data], data.get("message", "-"), data.get("statusCode", "-")

    return [], "-", "-"


def extract_fields(obj, message, status_code):
    vin = obj.get("vin")
    device = obj.get("deviceId")

    if not vin and not device:
        return None

    return {
        "VIN": vin,
        "DeviceID": device,
        "Carrier": obj.get("carrier"),
        "SimPackage": obj.get("simPackage"),
        "Result": message,
        "StatusCode": status_code
    }


def parse_text_auto(text):
    results = []

    blocks = extract_json_blocks(text)

    for block in blocks:
        data = try_parse_json(block)
        if not data:
            continue

        objs, message, status_code = normalize_to_list(data)

        for obj in objs:
            if isinstance(obj, dict):
                row = extract_fields(obj, message, status_code)
                if row:
                    results.append(row)

    return results


# =========================
# UNIVERSAL PARSER (ใช้กับทุกไฟล์)
# =========================
def process_file(df_raw):
    rows = []

    for col in df_raw.columns:
        for val in df_raw[col]:
            if pd.isna(val):
                continue

            text = str(val)

            uuid = extract_uuid(text)
            parsed = parse_text_auto(text)

            for item in parsed:
                item["UUID"] = uuid
                rows.append(item)

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.drop_duplicates(subset=["VIN", "DeviceID"])
        df = df.reset_index(drop=True)
        df.insert(0, "No.", df.index + 1)

    return df


# =========================
# UPLOAD
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    b2c_file = st.file_uploader("B2CDataHub", type=["xlsx", "csv"])

with col2:
    tcap_file = st.file_uploader("B2CTCAP", type=["xlsx", "csv"])

with col3:
    req_file = st.file_uploader("VehicleSettingRequester", type=["xlsx", "csv"])


# =========================
# MAIN
# =========================
if b2c_file and tcap_file and req_file:

    df_b2c_raw = pd.read_csv(b2c_file) if b2c_file.name.endswith(".csv") else pd.read_excel(b2c_file)
    df_tcap_raw = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)
    df_req_raw = pd.read_csv(req_file) if req_file.name.endswith(".csv") else pd.read_excel(req_file)

    # 👇 ใช้ parser เดียวกันทั้งหมด
    df_b2c = process_file(df_b2c_raw)
    df_tcap = process_file(df_tcap_raw)
    df_req = process_file(df_req_raw)

    # =========================
    # HIGHLIGHT
    # =========================
    def highlight_error(row):
        return ['background-color: #ffcccc' if str(row["StatusCode"]) != "200" else '' for _ in row]

    # =========================
    # SHOW
    # =========================
    st.subheader("B2CDataHubLinkage")
    st.dataframe(df_b2c.style.apply(highlight_error, axis=1))

    st.subheader("B2CTCAPLinkage")
    st.dataframe(df_tcap.style.apply(highlight_error, axis=1))

    st.subheader("VehicleSettingRequester")
    st.dataframe(df_req.style.apply(highlight_error, axis=1))

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_b2c.to_excel(writer, index=False, sheet_name='B2CDataHubLinkage')
        df_tcap.to_excel(writer, index=False, sheet_name='B2CTCAPLinkage')
        df_req.to_excel(writer, index=False, sheet_name='VehicleSettingRequester')

    output.seek(0)

    st.download_button(
        "Download Excel (3 Sheets)",
        data=output,
        file_name="B2C_AUTO.xlsx"
    )
