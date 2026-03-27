import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN UUID", layout="wide")
st.title("ITOSE Tools - VIN + UUID (Datahub Only)")

# =========================
# REGEX
# =========================
VIN_REGEX_LIST = [
    r'"vin"\s*:\s*"([^"]+)"',
    r'VIN[:=]\s*([A-Za-z0-9]+)',
    r'\b([A-HJ-NPR-Z0-9]{17})\b'
]

UUID_REGEX = r'([a-f0-9\-]{36})'

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

    vin_map = {}

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            vins = extract_vins(text)
            if not vins:
                continue

            uuid_match = re.search(UUID_REGEX, text)
            uuid = uuid_match.group(1) if uuid_match else ""

            for vin in vins:
                # overwrite → เอาค่าล่าสุดของ VIN
                vin_map[vin] = {
                    "VIN": vin,
                    "UUID": uuid
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

        st.subheader("VIN + UUID")
        st.dataframe(df_vin, use_container_width=True)

        # preview
        st.write("Sample (20 แถวแรก):")
        st.dataframe(df_vin.head(20), use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_UUID')

        output.seek(0)

        st.download_button(
            "Download VIN + UUID",
            data=output,
            file_name="vin-uuid.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN → regex อาจไม่ match format log")
