import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Based", layout="wide")
st.title("TCAPLinkageDatahub → VIN Based Clean")

# =========================
# FUNCTIONS
# =========================
def clean_result(msg):
    if not msg:
        return None
    if "success" in msg.lower():
        return "Operation Success"
    return msg

def get_uuid(text):
    m = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})', text)
    return m.group(1) if m else None

def extract_json(text):
    try:
        start = text.find("{")
        if start == -1:
            return None
        return json.loads(text[start:])
    except:
        return None

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    vin_map = {}

    # =========================
    # PARSE
    # =========================
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)

            uuid = get_uuid(text)
            json_data = extract_json(text)

            if not json_data:
                continue

            # =========================
            # HANDLE data STRUCTURE
            # =========================
            data_list = json_data.get("data", [])

            if isinstance(data_list, dict):
                data_list = [data_list]
            elif not isinstance(data_list, list):
                data_list = []

            # =========================
            # LOOP VIN
            # =========================
            for item in data_list:

                if not isinstance(item, dict):
                    continue

                vin = item.get("vin")
                if not vin:
                    continue

                device = item.get("deviceId")
                carrier = item.get("carrier")
                sim = item.get("simPackage")
                msg = json_data.get("message")  # root message
                date = item.get("Sendingtime")

                dt = pd.to_datetime(date, errors="coerce")

                record = {
                    "UUID": uuid,
                    "VIN": vin,
                    "DeviceID": device,
                    "Carrier": carrier if carrier else "Unknown",
                    "SimPackage": sim if sim else "Unknown",
                    "Result": clean_result(msg),
                    "_dt": dt
                }

                # =========================
                # KEEP LATEST PER VIN
                # =========================
                if vin not in vin_map or dt > vin_map[vin]["_dt"]:
                    vin_map[vin] = record

    # =========================
    # CHECK
    # =========================
    if not vin_map:
        st.error("❌ No VIN extracted → ตรวจ format log")
        st.stop()

    df_clean = pd.DataFrame(vin_map.values())

    # =========================
    # SORT
    # =========================
    df_clean = df_clean.sort_values("_dt", ascending=False)

    # =========================
    # SELECT COLUMNS
    # =========================
    df_clean = df_clean[[
        "UUID",
        "VIN",
        "DeviceID",
        "Carrier",
        "SimPackage",
        "Result"
    ]]

    df_clean = df_clean.reset_index(drop=True)
    df_clean.insert(0, "No.", df_clean.index + 1)

    # =========================
    # SUMMARY
    # =========================
    st.success(f"✅ Total VIN (Unique): {len(df_clean)}")

    # =========================
    # SHOW TABLE
    # =========================
    st.dataframe(df_clean, use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    df_clean.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Download Clean Data",
        data=output,
        file_name="vin_based_datahub.xlsx"
    )
