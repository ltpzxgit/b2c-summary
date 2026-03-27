import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Clean", layout="wide")
st.title("TCAPLinkageDatahub → VIN Clean (V5 Style)")

# =========================
# FUNCTIONS
# =========================
def get(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else "-"

def clean_result(msg):
    if msg == "-" or not msg:
        return "-"
    if "success" in msg.lower():
        return "Operation Success"
    return msg

def get_uuid(text):
    m = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})', text)
    return m.group(1) if m else "-"

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    # รวม log ทั้งหมด
    full_text = "\n".join(
        str(val) for col in df.columns for val in df[col] if pd.notna(val)
    )

    vin_map = {}

    # =========================
    # 🔥 ดึง VIN ทั้งหมดก่อน (สำคัญสุด)
    # =========================
    vins = re.findall(r'"vin":"([^"]+)"', full_text)

    for vin in vins:

        # หา block รอบ VIN (เอา context ใกล้ๆ)
        pattern = rf'.{{0,2000}}"vin":"{vin}".{{0,2000}}'
        match = re.search(pattern, full_text, re.DOTALL)

        if not match:
            continue

        block = match.group(0)

        uuid = get_uuid(block)
        device = get(r'"deviceId":"([^"]+)"', block)
        carrier = get(r'"carrier":"([^"]+)"', block)
        sim = get(r'"simPackage":"([^"]+)"', block)
        msg = get(r'"message":"([^"]+)"', block)
        date = get(r'"Sendingtime":"([^"]+)"', block)

        dt = pd.to_datetime(date, errors="coerce")

        record = {
            "UUID": uuid,
            "VIN": vin,
            "DeviceID": device,
            "Carrier": carrier,
            "SimPackage": sim,
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
        st.error("❌ ยัง parse ไม่ได้ → แต่ logic นี้ควรเอาอยู่แล้ว")
        st.stop()

    df_clean = pd.DataFrame(vin_map.values())

    # =========================
    # FORMAT
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

    df_clean = df_clean.fillna("-")

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
