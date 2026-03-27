import streamlit as st
import pandas as pd
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN JSON", layout="wide")
st.title("ITOSE Tools - VIN + DeviceID (JSON Correct)")

# =========================
# UPLOAD
# =========================
datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])

# =========================
# PROCESS (FULL JSON PARSE)
# =========================
if datahub_file:

    df = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)

    vin_map = {}

    for col in df.columns:
        for val in df[col]:

            if pd.isna(val):
                continue

            text = str(val)

            try:
                data = json.loads(text)

                # 🔥 case 1: เป็น list
                if isinstance(data, list):
                    for item in data:
                        vin = item.get("vin", "")
                        device = item.get("deviceId", "")

                        if vin:
                            vin_map[vin] = {
                                "VIN": vin,
                                "DeviceID": device
                            }

                # 🔥 case 2: เป็น dict
                elif isinstance(data, dict):
                    vin = data.get("vin", "")
                    device = data.get("deviceId", "")

                    if vin:
                        vin_map[vin] = {
                            "VIN": vin,
                            "DeviceID": device
                        }

            except:
                continue  # ข้ามเฉพาะอัน parse ไม่ได้

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
            file_name="vin-json-final.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN")
