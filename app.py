import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Clean", layout="wide")
st.title("TCAPLinkageDatahub → VIN Clean (FINAL FIX PRO)")

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

# 🔥 FIX สำคัญ: parse JSON แบบ balanced
def extract_json_objects(text):
    objs = []
    stack = 0
    start = None

    for i, char in enumerate(text):
        if char == '{':
            if stack == 0:
                start = i
            stack += 1

        elif char == '}':
            stack -= 1
            if stack == 0 and start is not None:
                objs.append(text[start:i+1])
                start = None

    return objs

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    # รวม text ทั้งหมด
    full_text = "\n".join(
        str(val) for col in df.columns for val in df[col] if pd.notna(val)
    )

    vin_map = {}

    # =========================
    # 🔥 extract JSON ถูกต้อง
    # =========================
    json_blocks = extract_json_objects(full_text)

    for block in json_blocks:

        try:
            data = json.loads(block)
        except:
            continue

        # UUID จาก block ใกล้ๆ (ย้อนหา)
        uuid = get_uuid(block)

        # =========================
        # HANDLE data[]
        # =========================
        data_list = data.get("data")

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
            msg = data.get("message")  # root
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

            # VIN primary → keep latest
            if vin not in vin_map or dt > vin_map[vin]["_dt"]:
                vin_map[vin] = record

    # =========================
    # CHECK
    # =========================
    if not vin_map:
        st.error("❌ No VIN extracted → log format ยังผิด")
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
