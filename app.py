import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN ROW", layout="wide")
st.title("ITOSE Tools - VIN + UUID + DeviceID")

# =========================
# REGEX
# =========================
VIN_REGEX_LIST = [
    r'"vin"\s*:\s*"([^"]+)"',
    r'VIN[:=]\s*([A-Za-z0-9]+)',
    r'\b([A-HJ-NPR-Z0-9]{17})\b'
]

UUID_REGEX = r'([a-f0-9\-]{36})'

DEVICE_REGEX_LIST = [
    r'"LDCMID"\s*:\s*"([^"]+)"',
    r'"deviceId"\s*:\s*"([^"]+)"',
    r'"deviceID"\s*:\s*"([^"]+)"',
    r'"ldcMid"\s*:\s*"([^"]+)"'
]

# =========================
# FUNCTIONS
# =========================
def extract_vins(text):
    vins = set()
    for pattern in VIN_REGEX_LIST:
        matches = re.findall(pattern, text)
        for m in matches:
            vins.add(m.strip())
    return vins

def extract_device(text):
    for pattern in DEVICE_REGEX_LIST:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""

# =========================
# UPLOAD
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if datahub_file:

    df = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)

    vin_map = {}

    # 🔥 ROW-BASED ONLY
    for _, row in df.iterrows():

        row_text = " ".join([str(v) for v in row if pd.notna(v)])

        vins = extract_vins(row_text)
        if not vins:
            continue

        uuid_match = re.search(UUID_REGEX, row_text)
        device = extract_device(row_text)

        uuid = uuid_match.group(1) if uuid_match else ""

        for vin in vins:

            # 🔥 FIX: ไม่ overwrite มั่ว
            if vin not in vin_map:
                vin_map[vin] = {
                    "VIN": vin,
                    "UUID": uuid,
                    "DeviceID": device
                }
            else:
                if uuid:
                    vin_map[vin]["UUID"] = uuid
                if device:
                    vin_map[vin]["DeviceID"] = device

    vin_list = list(vin_map.values())

    # =========================
    # SUMMARY
    # =========================
    st.markdown("### Summary")
    st.metric("VIN ทั้งหมด", len(vin_list))

    # =========================
    # TABLE
    # =========================
    if vin_list:

        df_vin = pd.DataFrame(vin_list)

        # กัน null
        df_vin["UUID"] = df_vin["UUID"].fillna("")
        df_vin["DeviceID"] = df_vin["DeviceID"].fillna("")

        df_vin = df_vin.reset_index(drop=True)
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.dataframe(df_vin, use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_DATA')

        output.seek(0)

        st.download_button(
            "Download",
            data=output,
            file_name="vin-row-final.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN")
