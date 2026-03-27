import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN DEVICE", layout="wide")
st.title("ITOSE Tools - VIN + DeviceID")

# =========================
# REGEX
# =========================
VIN_REGEX_LIST = [
    r'"vin"\s*:\s*"([^"]+)"',
    r'VIN[:=]\s*([A-Za-z0-9]+)',
    r'\b([A-HJ-NPR-Z0-9]{17})\b'
]

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
# PROCESS (DEVICE BLOCK)
# =========================
if datahub_file:

    df = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)

    vin_map = {}

    current_device = ""

    for col in df.columns:
        for val in df[col]:

            if pd.isna(val):
                continue

            text = str(val)

            # 🔥 เจอ Device = เริ่ม block ใหม่
            device = extract_device(text)
            if device:
                current_device = device

            # หา VIN
            vins = extract_vins(text)
            if not vins:
                continue

            for vin in vins:
                vin_map[vin] = {
                    "VIN": vin,
                    "DeviceID": current_device
                }

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

        df_vin = pd.DataFrame(vin_list).fillna("")
        df_vin = df_vin.reset_index(drop=True)
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.dataframe(df_vin, use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_DEVICE')

        output.seek(0)

        st.download_button(
            "Download",
            data=output,
            file_name="vin-device.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN")
