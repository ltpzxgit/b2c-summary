import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - AUTO SPLIT", layout="wide")
st.title("ITOSE Tools - Auto Detect (Split by File)")

# =========================
# REGEX
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'
JSON_BLOCK_REGEX = r'\{.*?\}'

# =========================
# CORE
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
# EXTRACT (รวมทุก type)
# =========================
def extract_row(obj, uuid):
    return {
        "UUID": uuid,
        "VIN": obj.get("vin"),
        "DeviceID": obj.get("deviceId") or obj.get("resourceGroupId"),
        "Carrier": obj.get("carrier"),
        "SimPackage": obj.get("simPackage"),
        "IMEI": obj.get("IMEI"),
        "ICCID": obj.get("ICCID"),
        "IMSI": obj.get("IMSI"),
        "ProdStatus": obj.get("prodStatus"),
        "SendDate": obj.get("sendDate"),
        "TypeStatus": obj.get("typeStatus"),
        "Result": obj.get("message") or obj.get("resultDesc"),
        "StatusCode": obj.get("statusCode") or obj.get("resultCode")
    }


# =========================
# PARSE FILE (แยกอิสระ)
# =========================
def parse_file(df):
    rows = []

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

                    row = extract_row(obj, uuid)

                    # กัน row ขยะ
                    if not row["VIN"] and not row["DeviceID"]:
                        continue

                    rows.append(row)

    df_out = pd.DataFrame(rows)

    if not df_out.empty:
        df_out = df_out.drop_duplicates()
        df_out.reset_index(drop=True, inplace=True)
        df_out.insert(0, "No.", df_out.index + 1)

    return df_out


# =========================
# UPLOAD
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    file1 = st.file_uploader("File 1 (B2CDataHub)", type=["xlsx", "csv"])

with col2:
    file2 = st.file_uploader("File 2 (B2CTCAP)", type=["xlsx", "csv"])

with col3:
    file3 = st.file_uploader("File 3 (VehicleSettingRequester)", type=["xlsx", "csv"])


# =========================
# MAIN
# =========================
if file1 and file2 and file3:

    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
    df3 = pd.read_csv(file3) if file3.name.endswith(".csv") else pd.read_excel(file3)

    out1 = parse_file(df1)
    out2 = parse_file(df2)
    out3 = parse_file(df3)

    # =========================
    # SHOW
    # =========================
    st.subheader("B2CDataHubLinkage")
    st.dataframe(out1)

    st.subheader("B2CTCAPLinkage")
    st.dataframe(out2)

    st.subheader("VehicleSettingRequester")
    st.dataframe(out3)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        out1.to_excel(writer, index=False, sheet_name='B2CDataHubLinkage')
        out2.to_excel(writer, index=False, sheet_name='B2CTCAPLinkage')
        out3.to_excel(writer, index=False, sheet_name='VehicleSettingRequester')

    output.seek(0)

    st.download_button(
        "Download Excel (Split Sheets)",
        data=output,
        file_name="AUTO_SPLIT.xlsx"
    )
