import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - FINAL", layout="wide")
st.title("ITOSE Tools - B2C Final Version")

# =========================
# REGEX
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'

# =========================
# B2C PARSER (ของเดิมเทพๆ)
# =========================
def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else "-"


def safe_json(text):
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None

        json_part = text[start:end+1]
        json_part = json_part.replace('\\"', '"')

        return json.loads(json_part)
    except:
        return None


def parse_b2c(text):
    data = safe_json(text)
    if not data:
        return []

    results = []

    try:
        if isinstance(data, list):
            vehicles = data
            message = "-"
            status = "-"
        elif "data" in data:
            vehicles = data.get("data", [])
            message = data.get("message", "-")
            status = data.get("statusCode", "-")
        else:
            vehicles = [data]
            message = data.get("message", "-")
            status = data.get("statusCode", "-")

        for v in vehicles:
            vin = v.get("vin")
            device = v.get("deviceId")

            if not vin and not device:
                continue

            results.append({
                "UUID": "-",
                "VIN": vin,
                "DeviceID": device,
                "Carrier": v.get("carrier"),
                "SimPackage": v.get("simPackage"),
                "Result": message,
                "StatusCode": status
            })

    except:
        pass

    return results


# =========================
# UPLOAD
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    file1 = st.file_uploader("B2CDataHub", type=["xlsx", "csv"])

with col2:
    file2 = st.file_uploader("B2CTCAP", type=["xlsx", "csv"])

with col3:
    file3 = st.file_uploader("VehicleSettingRequester", type=["xlsx", "csv"])


# =========================
# MAIN
# =========================
if file1 and file2 and file3:

    df1_raw = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
    df3 = pd.read_csv(file3) if file3.name.endswith(".csv") else pd.read_excel(file3)

    # =========================
    # PARSE B2C ONLY
    # =========================
    rows = []

    for col in df1_raw.columns:
        for val in df1_raw[col]:
            if pd.isna(val):
                continue

            text = str(val)
            uuid = extract_uuid(text)

            parsed = parse_b2c(text)

            for item in parsed:
                item["UUID"] = uuid
                rows.append(item)

    df1 = pd.DataFrame(rows)

    if not df1.empty:
        df1 = df1.drop_duplicates(subset=["VIN", "DeviceID"])
        df1.reset_index(drop=True, inplace=True)
        df1.insert(0, "No.", df1.index + 1)

    # =========================
    # SHOW
    # =========================
    st.subheader("B2CDataHubLinkage")
    if not df1.empty:
        st.dataframe(df1)
    else:
        st.warning("No data parsed from B2CDataHub")

    st.subheader("B2CTCAPLinkage")
    st.dataframe(df2)

    st.subheader("VehicleSettingRequester")
    st.dataframe(df3)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df1.to_excel(writer, index=False, sheet_name='B2CDataHubLinkage')
        df2.to_excel(writer, index=False, sheet_name='B2CTCAPLinkage')
        df3.to_excel(writer, index=False, sheet_name='VehicleSettingRequester')

    output.seek(0)

    st.download_button(
        "Download Excel",
        data=output,
        file_name="B2C_Final.xlsx"
    )
