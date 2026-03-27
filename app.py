import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C 3 Files", layout="wide")
st.title("ITOSE Tools - B2C (3 Files Version)")

# =========================
# REGEX
# =========================
UUID_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})'

# =========================
# FUNCTIONS
# =========================
def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else "-"


def safe_json_load(text):
    """
    โหลด JSON แบบทน:
    - ตัดจาก { ตัวแรก
    - แก้ escaped json
    """
    try:
        json_part = text[text.index("{"):]

        # กรณี escape "\""
        json_part = json_part.replace('\\"', '"')

        return json.loads(json_part)
    except:
        return None


def parse_b2c_block(text):
    data = safe_json_load(text)
    if not data:
        return []

    results = []

    try:
        # 🔥 รองรับทุกเคส
        if isinstance(data, list):
            vehicles = data
            message = "-"
            status_code = "-"
        elif "data" in data:
            vehicles = data.get("data", [])
            message = data.get("message", "-")
            status_code = data.get("statusCode", "-")
        else:
            vehicles = [data]
            message = data.get("message", "-")
            status_code = data.get("statusCode", "-")

        for v in vehicles:
            vin = v.get("vin")
            device = v.get("deviceId")

            # กันเคสไม่มีค่า
            if not vin and not device:
                continue

            results.append({
                "VIN": vin,
                "DeviceID": device,
                "Carrier": v.get("carrier"),
                "SimPackage": v.get("simPackage"),
                "Result": message,
                "StatusCode": status_code
            })

    except:
        pass

    return results


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
    df_tcap = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)
    df_req = pd.read_csv(req_file) if req_file.name.endswith(".csv") else pd.read_excel(req_file)

    # =========================
    # B2C PARSE
    # =========================
    rows = []

    for col in df_b2c_raw.columns:
        for val in df_b2c_raw[col]:
            if pd.isna(val):
                continue

            text = str(val)

            uuid = extract_uuid(text)

            parsed = parse_b2c_block(text)

            if not parsed:
                continue  # skip เงียบๆ

            for item in parsed:
                item["UUID"] = uuid
                rows.append(item)

    df_b2c = pd.DataFrame(rows)

    if not df_b2c.empty:
        df_b2c = df_b2c.drop_duplicates(subset=["VIN", "DeviceID"])
        df_b2c = df_b2c.reset_index(drop=True)
        df_b2c.insert(0, "No.", df_b2c.index + 1)

    # =========================
    # HIGHLIGHT ERROR
    # =========================
    def highlight_error(row):
        return ['background-color: #ffcccc' if str(row["StatusCode"]) != "200" else '' for _ in row]

    # =========================
    # SHOW
    # =========================
    st.subheader("B2CDataHubLinkage")
    if not df_b2c.empty:
        st.dataframe(df_b2c.style.apply(highlight_error, axis=1))
    else:
        st.warning("No data parsed from B2CDataHub")

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
        "Download Excel (3 Sheets)",
        data=output,
        file_name="B2C_3Files.xlsx"
    )
