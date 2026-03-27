import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - VIN Based", layout="wide")
st.title("TCAPLinkageDatahub → VIN Based Clean")

# =========================
# FUNCTIONS
# =========================
def get(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None

def clean_result(msg):
    if not msg:
        return None
    if "success" in msg.lower():
        return "Operation Success"
    return msg

def get_carrier(deviceid, carrier):
    if carrier:
        return carrier
    if isinstance(deviceid, str) and deviceid.startswith(("A","Z")):
        return "AIS"
    return "TRUE"

def extract(text):
    vin = get(r'"vin":"([^"]+)"', text)
    if not vin:
        return None

    device = get(r'"deviceId":"([^"]+)"', text)
    carrier = get(r'"carrier":"([^"]+)"', text)
    sim = get(r'"simPackage":"([^"]+)"', text)
    msg = get(r'"message":"([^"]+)"', text)
    uuid = get(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ([a-f0-9\-]{36})', text)
    date = get(r'"Sendingtime":"([^"]+)"', text)

    return {
        "VIN": vin,
        "UUID": uuid,
        "DeviceID": device,
        "Carrier": get_carrier(device, carrier),
        "SimPackage": sim if sim else "Unknown",
        "Result": clean_result(msg),
        "Date": date
    }

# =========================
# UPLOAD
# =========================
file = st.file_uploader("Upload TCAPLinkageDatahub", type=["xlsx","csv"])

if file:

    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    vin_map = {}

    # =========================
    # BUILD BY VIN
    # =========================
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            data = extract(text)

            if not data:
                continue

            vin = data["VIN"]

            # convert date
            dt = pd.to_datetime(data["Date"], errors="coerce")

            # ถ้ายังไม่มี VIN หรือเจอใหม่กว่า → overwrite
            if vin not in vin_map or dt > vin_map[vin]["_dt"]:
                data["_dt"] = dt
                vin_map[vin] = data

    # =========================
    # CHECK
    # =========================
    if not vin_map:
        st.error("❌ No VIN extracted")
        st.stop()

    df_clean = pd.DataFrame(vin_map.values())

    # =========================
    # FINAL FORMAT
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
    # SHOW
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
        file_name="vin_based_datahub.xlsx"
    )
