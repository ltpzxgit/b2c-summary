import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - AUTO ALL", layout="wide")
st.title("ITOSE Tools - Auto Detect (3 Sheets)")

# =========================
# REGEX
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'
JSON_BLOCK_REGEX = r'\{.*?\}'

# =========================
# CORE PARSER
# =========================
def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else "-"


def extract_blocks(text):
    return re.findall(JSON_BLOCK_REGEX, text)


def parse_json(block):
    try:
        block = block.replace('\\"', '"')
        return json.loads(block)
    except:
        return None


def normalize(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        return [data]
    return []


# =========================
# AUTO DETECT TYPE
# =========================
def classify(obj):
    keys = obj.keys()

    if "vin" in keys and "deviceId" in keys:
        return "B2C"

    if "IMEI" in keys or "ICCID" in keys:
        return "TCAP"

    if "resultCode" in keys or "resourceOrderId" in keys:
        return "REQ"

    return None


# =========================
# EXTRACTORS
# =========================
def extract_b2c(obj, uuid):
    return {
        "UUID": uuid,
        "VIN": obj.get("vin"),
        "DeviceID": obj.get("deviceId"),
        "Carrier": obj.get("carrier"),
        "SimPackage": obj.get("simPackage"),
        "Result": obj.get("message", "-"),
        "StatusCode": obj.get("statusCode", "-")
    }


def extract_tcap(obj, uuid):
    return {
        "UUID": uuid,
        "DeviceID": obj.get("deviceId"),
        "IMEI": obj.get("IMEI"),
        "ICCID": obj.get("ICCID"),
        "IMSI": obj.get("IMSI"),
        "ProdStatus": obj.get("prodStatus"),
        "SendDate": obj.get("sendDate"),
        "TypeStatus": obj.get("typeStatus")
    }


def extract_req(obj, uuid):
    return {
        "UUID": uuid,
        "DeviceID": obj.get("resourceGroupId"),
        "ResourceOrderId": obj.get("resourceOrderId"),
        "ResultCode": obj.get("resultCode"),
        "ResultDesc": obj.get("resultDesc")
    }


# =========================
# PARSE FILE GENERIC
# =========================
def parse_file(df):
    b2c_rows = []
    tcap_rows = []
    req_rows = []

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            uuid = extract_uuid(text)

            blocks = extract_blocks(text)

            for block in blocks:
                data = parse_json(block)
                if not data:
                    continue

                objs = normalize(data)

                for obj in objs:
                    if not isinstance(obj, dict):
                        continue

                    t = classify(obj)

                    if t == "B2C":
                        row = extract_b2c(obj, uuid)
                        if row["VIN"] or row["DeviceID"]:
                            b2c_rows.append(row)

                    elif t == "TCAP":
                        tcap_rows.append(extract_tcap(obj, uuid))

                    elif t == "REQ":
                        req_rows.append(extract_req(obj, uuid))

    return b2c_rows, tcap_rows, req_rows


# =========================
# UPLOAD
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    file1 = st.file_uploader("File 1", type=["xlsx", "csv"])

with col2:
    file2 = st.file_uploader("File 2", type=["xlsx", "csv"])

with col3:
    file3 = st.file_uploader("File 3", type=["xlsx", "csv"])


# =========================
# MAIN
# =========================
if file1 and file2 and file3:

    dfs = []
    for f in [file1, file2, file3]:
        df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
        dfs.append(df)

    all_b2c, all_tcap, all_req = [], [], []

    for df in dfs:
        b2c, tcap, req = parse_file(df)
        all_b2c.extend(b2c)
        all_tcap.extend(tcap)
        all_req.extend(req)

    df_b2c = pd.DataFrame(all_b2c).drop_duplicates()
    df_tcap = pd.DataFrame(all_tcap).drop_duplicates()
    df_req = pd.DataFrame(all_req).drop_duplicates()

    # numbering
    for df in [df_b2c, df_tcap, df_req]:
        if not df.empty:
            df.reset_index(drop=True, inplace=True)
            df.insert(0, "No.", df.index + 1)

    # =========================
    # SHOW
    # =========================
    st.subheader("B2CDataHubLinkage")
    st.dataframe(df_b2c)

    st.subheader("B2CTCAPLinkage")
    st.dataframe(df_tcap)

    st.subheader("VehicleSettingRequester")
    st.dataframe(df_req)

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
        "Download Excel (Auto Detect)",
        data=output,
        file_name="AUTO_ALL.xlsx"
    )
