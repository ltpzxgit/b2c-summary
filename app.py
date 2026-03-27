import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Debug", layout="wide")
st.title("ITOSE Tools - VIN Debug (Datahub Only)")

# =========================
# REGEX (VIN SMART)
# =========================
VIN_REGEX_LIST = [
    r'"vin"\s*:\s*"([^"]+)"',
    r'VIN[:=]\s*([A-Za-z0-9]+)',
    r'\b([A-HJ-NPR-Z0-9]{17})\b'
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

# =========================
# UPLOAD (เหมือนของเดิม)
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if datahub_file:

    df = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)

    vin_set = set()

    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            vins = extract_vins(str(val))
            for v in vins:
                vin_set.add(v)

    vin_list = sorted(vin_set)

    # =========================
    # SUMMARY
    # =========================
    st.markdown("### Summary")
    st.metric("VIN ทั้งหมด", len(vin_list))

    # =========================
    # TABLE
    # =========================
    if vin_list:

        df_vin = pd.DataFrame(vin_list, columns=["VIN"])
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.subheader("VIN List")
        st.dataframe(df_vin, use_container_width=True)

        # =========================
        # EXPORT
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vin.to_excel(writer, index=False, sheet_name='VIN_List')

        output.seek(0)

        st.download_button(
            "Download VIN List",
            data=output,
            file_name="vin-list.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN → format log อาจไม่ตรง")
