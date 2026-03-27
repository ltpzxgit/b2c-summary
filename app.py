import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN FULL", layout="wide")
st.title("ITOSE Tools - VIN + DeviceID + Carrier + SimPackage")

# =========================
# FUNCTIONS
# =========================
def extract_json(text):
    match = re.search(r'(\[.*\])', text)
    if match:
        return match.group(1)

    match = re.search(r'(\{.*\})', text)
    if match:
        return match.group(1)

    return None

def map_sim(sim):
    if sim == "C":
        return "Commercial"
    elif sim == "R":
        return "Registration"
    return sim or ""

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

            json_str = extract_json(text)
            if not json_str:
                continue

            try:
                data = json.loads(json_str)

                # =========================
                # LIST CASE
                # =========================
                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        device = item.get("deviceId", "")
                        carrier = item.get("carrier", "")
                        sim = map_sim(item.get("simPackage", ""))

                        if vin:
                            vin_map[vin] = {
                                "VIN": vin,
                                "DeviceID": device,
                                "Carrier": carrier,
                                "SimPackage": sim
                            }

                # =========================
                # DICT CASE
                # =========================
                elif isinstance(data, dict):

                    vin = data.get("vin", "")
                    device = data.get("deviceId", "")
                    carrier = data.get("carrier", "")
                    sim = map_sim(data.get("simPackage", ""))

                    if vin:
                        vin_map[vin] = {
                            "VIN": vin,
                            "DeviceID": device,
                            "Carrier": carrier,
                            "SimPackage": sim
                        }

            except:
                continue

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
            df_vin.to_excel(writer, index=False, sheet_name='VIN_FULL')

        output.seek(0)

        st.download_button(
            "Download",
            data=output,
            file_name="vin-full.xlsx"
        )

    else:
        st.error("❌ ไม่เจอ VIN")
