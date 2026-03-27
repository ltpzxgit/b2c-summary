import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Clean", layout="wide")
st.title("TCAPLinkageDatahub → VIN Clean (Based on V5 Logic)")

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

def extract_json_block(text):
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start:end+1])
    except:
        return None

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    # =========================
    # รวม log ทั้งหมด (เหมือน v5)
    # =========================
    full_text = "\n".join(
        str(val) for col in df.columns for val in df[col] if pd.notna(val)
    )

    # =========================
    # split เป็น block ตาม UUID
    # =========================
    blocks = re.split(r'(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', full_text)

    vin_map = {}

    # =========================
    # PARSE BLOCK
    # =========================
    for block in blocks:

        uuid = get_uuid(block)
        json_data = extract_json_block(block)

        if not json_data:
            continue

        data_list = json_data.get("data", [])

        if isinstance(data_list, dict):
            data_list = [data_list]
        elif not isinstance(data_list, list):
            continue

        for item in data_list:

            if not isinstance(item, dict):
                continue

            vin = item.get("vin")
            if not vin:
                continue

            device = item.get("deviceId")
            carrier = item.get("carrier")
            sim = item.get("simPackage")
            msg = json_data.get("message")
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
            # VIN PRIMARY (เอาล่าสุด)
            # =========================
            if vin not in vin_map or dt > vin_map[vin]["_dt"]:
                vin_map[vin] = record

    # =========================
    # CHECK
    # =========================
    if not vin_map:
        st.error("❌ No VIN extracted → log ยัง parse ไม่ได้")
        st.stop()

    df_clean = pd.DataFrame(vin_map.values())

    # =========================
    # SORT + FORMAT
    # =========================
    df_clean = df_clean.sort_values("_dt", ascending=False)

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
    # RESULT
    # =========================
    st.success(f"✅ Total VIN: {len(df_clean)}")
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
        file_name="vin_clean.xlsx"
    )
