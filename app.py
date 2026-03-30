import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C", layout="wide")
st.title("ITOSE Tools - B2C Summary")

# =========================
# UI STYLE (เหมือนเดิม 100%)
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Upload Compact */
[data-testid="stFileUploader"] > div {
    padding: 8px !important;
}

[data-testid="stFileUploader"] section {
    padding: 14px !important;
    border-radius: 12px !important;
}

[data-testid="stFileUploader"] p {
    font-size: 14px !important;
}

[data-testid="stFileUploader"] button {
    padding: 6px 12px !important;
    font-size: 13px !important;
}

[data-testid="stFileUploader"] {
    margin-bottom: 10px !important;
}

[data-testid="stFileUploader"] section div {
    gap: 6px !important;
}

/* Summary Card */
.summary-card {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid #334155;
}

.summary-title {
    color: #94a3b8;
    font-size: 16px;
}

.summary-number {
    color: white;
    font-size: 48px;
    font-weight: 700;
    margin: 10px 0;
}

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
# FUNCTIONS
# =========================
def extract_json(text):
    match = re.search(r'(\[.*\])', text)  # ไม่แตะ
    return match.group(1) if match else None

def map_sim(sim):
    return "Commercial" if sim == "C" else "Registration" if sim == "R" else sim or ""

def extract_tail(text):
    response, status, message = "", "", ""

    # fix double quote
    text = text.replace('""', '"')

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
# FILE 1 (เดิม 100%)
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
# FILE 2 (UUID Mapping)
# =========================
def process_file_v2(df):
    rows = []
    response_map = {}

    # pass 1: เก็บ response ทั้งไฟล์
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

    # pass 2: map VIN
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

def summary_card(title, total, error):
    st.markdown(f"""
    <div class="summary-card">
        <div class="summary-title">{title}</div>
        <div class="summary-number">{total}</div>
        <div class="summary-error">Error: {error}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# UPLOAD
# =========================
file1 = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])
file2 = st.file_uploader("TCAPLinkage", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if file1:

    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    rows1 = process_file(df1)

    df_vin1 = pd.DataFrame(rows1).fillna("")
    df_vin1 = df_vin1.reset_index(drop=True)
    df_vin1.insert(0, "No.", df_vin1.index + 1)

    df_vin2 = pd.DataFrame()

    if file2:
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
        rows2 = process_file_v2(df2)

        df_vin2 = pd.DataFrame(rows2).fillna("")
        df_vin2 = df_vin2.reset_index(drop=True)
        df_vin2.insert(0, "No.", df_vin2.index + 1)

        df_vin2 = df_vin2[[
            "No.", "UUID", "VIN", "DeviceID",
            "Response Message", "StatusCode"
        ]]

    # =========================
    # SUMMARY
    # =========================
    st.markdown("## Summary")

    cards = []
    cards.append(("TCAPLinkageDatahub", len(df_vin1), 0))

    if not df_vin2.empty:
        cards.append(("TCAPLinkage", len(df_vin2), 0))

    cols = st.columns(len(cards))

    for i, (title, total, error) in enumerate(cards):
        with cols[i]:
            summary_card(title, total, error)

    # =========================
    # TABLE
    # =========================
    st.markdown("### TCAPLinkageDatahub")
    st.dataframe(df_vin1, use_container_width=True)

    if not df_vin2.empty:
        st.markdown("### TCAPLinkage")
        st.dataframe(df_vin2, use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        df_vin1.to_excel(writer, index=False, sheet_name='TCAPLinkageDataHub')

        if not df_vin2.empty:
            df_vin2.to_excel(writer, index=False, sheet_name='TCAPLinkage')

        summary_data = [
            {"Source": "TCAPLinkageDatahub", "Total": len(df_vin1), "Error": 0}
        ]

        if not df_vin2.empty:
            summary_data.append({
                "Source": "TCAPLinkage",
                "Total": len(df_vin2),
                "Error": 0
            })

        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')

    output.seek(0)

    st.download_button(
        "Download",
        data=output,
        file_name="b2c-summary.xlsx"
    )

else:
    st.info("Please upload 1st file first")
