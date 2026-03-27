import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Clean", layout="wide")
st.title("TCAPLinkageDatahub → VIN Clean (FINAL FIX)")

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
    # 🔥 ดึง JSON ทุกก้อน
    # =========================
    json_blocks = re.findall(r'\{.*?\}', full_text, re.DOTALL)

    for block in json_blocks:

        try:
            data = json.loads(block)
        except:
            continue

        # ต้องมี vin ถึงจะสนใจ
        vin = data.get("vin")
        if not vin:
            continue

        device = data.get("deviceId")
        carrier = data.get("carrier")
        sim = data.get("simPackage")
        msg = data.get("message")
        date = data.get("Sendingtime")

        # UUID หาใน block ใกล้ๆ
        uuid = get_uuid(full_text)

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

        if vin not in vin_map or dt > vin_map[vin]["_dt"]:
            vin_map[vin] = record

    # =========================
    # CHECK
    # =========================
    if not vin_map:
        st.error("❌ ยังไม่ได้ → log ซ้อนลึกเกิน ต้องใช้ parser ขั้นสูง")
        st.stop()

    df_clean = pd.DataFrame(vin_map.values())

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

    st.success(f"✅ Total VIN: {len(df_clean)}")
    st.dataframe(df_clean, use_container_width=True)

    output = BytesIO()
    df_clean.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Download Clean Data",
        data=output,
        file_name="vin_clean.xlsx"
    )
