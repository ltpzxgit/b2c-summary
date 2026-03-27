import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN BLOCK", layout="wide")
st.title("ITOSE Tools - VIN + UUID + DeviceID (Block Mode)")

# =========================
# REGEX
# =========================
VIN_REGEX_LIST = [
    r'"vin"\s*:\s*"([^"]+)"',
    r'VIN[:=]\s*([A-Za-z0-9]+)',
    r'\b([A-HJ-NPR-Z0-9]{17})\b'
]

UUID_REGEX = r'([a-f0-9\-]{36})'
DEVICE_REGEX = r'"LDCMID"\s*:\s*"([^"]+)"'

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

# =========================
# UPLOAD
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if datahub_file:

    df = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)

    # 🔥 รวมทุก column เป็น text เดียว
    full_text = ""
    for col in df.columns:
        for val in df[col]:
            if pd.notna(val):
                full_text += str(val) + "\n"

    # 🔥 split เป็น block (JSON style)
    blocks = re.findall(r'\{.*?\}', full_text, re.DOTALL)

    vin_map = {}

    for block in blocks:

        vins = extract_vins(block)
        if not vins:
            continue

        uuid_match = re.search(UUID_REGEX, block)
        device_match = re.search(DEVICE_REGEX, block)

        uuid = uuid_match.group(1) if uuid_match else ""
        device = device_match.group(1) if device_match else ""

        for vin in vins:
            vin_map[vin] = {
                "VIN": vin,
                "UUID": uuid,
                "DeviceID": device
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

        df_vin = pd.DataFrame(vin_list)
        df_vin = df_vin.reset_index(drop=True)
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.subheader("VIN + UUID + DeviceID (Block)")
        st.dataframe(df_vin, use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_BLOCK')

        output.seek(0)

        st.download_button(
            "Download",
            data=output,
            file_name="vin-block.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN ใน block")
