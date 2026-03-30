import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C", layout="wide")
st.title("ITOSE Tools - B2C Summary")

# =========================
# UI STYLE
# =========================
st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
.summary-card {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid #334155;
}
.summary-title { color: #94a3b8; font-size: 16px; }
.summary-number { color: white; font-size: 48px; font-weight: 700; }
.summary-error {
    margin-top: 10px;
    padding: 10px;
    border-radius: 12px;
    border: 1px solid #22c55e;
    color: #22c55e;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNCTIONS (COMMON)
# =========================
def extract_json(text):
    match = re.search(r'(\[.*\])', text)  # ❗ ของเดิม (ไม่แตะ)
    return match.group(1) if match else None

def map_sim(sim):
    return "Commercial" if sim == "C" else "Registration" if sim == "R" else sim or ""

def extract_tail(text):
    response, status, message = "", "", ""

    text = text.replace('""', '"')  # ✅ fix double quote

    m1 = re.search(r'"message"\s*:\s*"([^"]+)"\s*,\s*"statusCode"', text)
    if m1:
        response = m1.group(1)

    m2 = re.search(r'"statusCode"\s*:\s*"?(\d+)"?', text)
    if m2:
        status = m2.group(1)

    m3 = re.search(r'"message"\s*:\s*"([^"]+)"', text)
    if m3:
        msg_val = m3.group(1)
        if "Process" in msg_val:
            message = msg_val

    return response, status, message

UUID_REGEX = r'([a-f0-9\-]{36})'
def extract_uuid(text):
    m = re.search(UUID_REGEX, text)
    return m.group(1) if m else ""

# =========================
# FILE 1 (❗ ORIGINAL - ห้ามแตะ)
# =========================
def process_file(df):
    rows = []

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

                response, status, msg = extract_tail(text)
                uuid = extract_uuid(text)

                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        if not vin:
                            continue

                        rows.append({
                            "UUID": uuid,
                            "VIN": vin,
                            "DeviceID": item.get("deviceId", ""),
                            "Carrier": item.get("carrier", ""),
                            "SimPackage": map_sim(item.get("simPackage", "")),
                            "Response Message": response,
                            "StatusCode": status,
                            "Message": msg
                        })

            except:
                continue

    return rows

# =========================
# FILE 2 (✅ FIX UUID MATCHING)
# =========================
def process_file_v2(df):
    rows = []
    response_map = {}

    # PASS 1: เก็บ response
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            uuid = extract_uuid(text)

            if "response body" in text:
                response, status, msg = extract_tail(text)
                if uuid:
                    response_map[uuid] = (response, status, msg)

    # PASS 2: VIN
    for col in df.columns:
        for val in df[col]:
            if pd.isna(val):
                continue

            text = str(val)
            uuid = extract_uuid(text)

            json_str = extract_json(text)
            if not json_str:
                continue

            try:
                data = json.loads(json_str)

                response, status, msg = response_map.get(uuid, ("", "", ""))

                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        if not vin:
                            continue

                        rows.append({
                            "UUID": uuid,
                            "VIN": vin,
                            "DeviceID": item.get("deviceId", ""),
                            "Carrier": item.get("carrier", ""),
                            "SimPackage": map_sim(item.get("simPackage", "")),
                            "Response Message": response,
                            "StatusCode": status,
                            "Message": msg
                        })

            except:
                continue

    return rows

# =========================
# UI
# =========================
file1 = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])
file2 = st.file_uploader("TCAPLinkage", type=["xlsx", "csv"])

if file1:

    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    rows1 = process_file(df1)

    df_vin1 = pd.DataFrame(rows1).fillna("")
    df_vin1.insert(0, "No.", range(1, len(df_vin1)+1))

    df_vin2 = pd.DataFrame()

    if file2:
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
        rows2 = process_file_v2(df2)

        df_vin2 = pd.DataFrame(rows2).fillna("")
        df_vin2.insert(0, "No.", range(1, len(df_vin2)+1))

        df_vin2 = df_vin2[[
            "No.", "UUID", "VIN", "DeviceID",
            "Response Message", "StatusCode"
        ]]

    # Summary
    st.markdown("## Summary")
    cols = st.columns(2 if not df_vin2.empty else 1)

    with cols[0]:
        st.markdown(f"<div class='summary-card'><div class='summary-title'>TCAPLinkageDatahub</div><div class='summary-number'>{len(df_vin1)}</div></div>", unsafe_allow_html=True)

    if not df_vin2.empty:
        with cols[1]:
            st.markdown(f"<div class='summary-card'><div class='summary-title'>TCAPLinkage</div><div class='summary-number'>{len(df_vin2)}</div></div>", unsafe_allow_html=True)

    # Tables
    st.dataframe(df_vin1, use_container_width=True)
    if not df_vin2.empty:
        st.dataframe(df_vin2, use_container_width=True)

    # Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_vin1.to_excel(writer, index=False, sheet_name='TCAPLinkageDataHub')
        if not df_vin2.empty:
            df_vin2.to_excel(writer, index=False, sheet_name='TCAPLinkage')

    output.seek(0)
    st.download_button("Download", data=output, file_name="b2c-summary.xlsx")

else:
    st.info("Please upload 1st file first")
