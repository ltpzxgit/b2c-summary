import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="VIN Extractor", layout="wide")
st.title("VIN Extractor (Smart Mode)")

# =========================
# REGEX (หลายแบบ กันพลาด)
# =========================
VIN_REGEX_LIST = [
    r'"vin"\s*:\s*"([^"]+)"',                 # JSON format
    r'VIN[:=]\s*([A-Za-z0-9]+)',             # VIN: xxx
    r'\b([A-HJ-NPR-Z0-9]{17})\b'             # VIN 17 ตัว (universal)
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
# UPLOAD
# =========================
datahub_file = st.file_uploader("Upload Datahub File", type=["xlsx", "csv"])

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

            text = str(val)
            vins = extract_vins(text)

            for v in vins:
                vin_set.add(v)

    vin_list = sorted(vin_set)

    # =========================
    # RESULT
    # =========================
    st.subheader("VIN List")

    st.write(f"เจอ VIN ทั้งหมด: {len(vin_list)}")

    if vin_list:

        df_vin = pd.DataFrame(vin_list, columns=["VIN"])
        df_vin.insert(0, "No.", df_vin.index + 1)

        st.dataframe(df_vin, use_container_width=True)

        # preview บางส่วน
        st.write("Sample VIN (20 ตัวแรก):")
        st.write(vin_list[:20])

        # download
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
        st.error("❌ ไม่เจอ VIN เลย → format log อาจไม่ตรง")
