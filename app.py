import streamlit as st
import pandas as pd
import re
import json
from io import BytesIO

st.set_page_config(page_title="ITOSE - DTEN Summary", layout="wide")
st.title("ITOSE Tools - DTEN Summary")

# =========================
# UI STYLE (เหมือนรูป)
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* summary card */
.summary-card {
    background: linear-gradient(145deg, #0f172a, #0b1220);
    border-radius: 20px;
    padding: 28px 20px;
    text-align: center;
    border: 1px solid rgba(59,130,246,0.15);
    box-shadow: 0 0 25px rgba(59,130,246,0.15);
    transition: 0.2s;
}

.summary-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 0 40px rgba(59,130,246,0.3);
}

/* title */
.summary-title {
    color: #94a3b8;
    font-size: 15px;
    margin-bottom: 10px;
}

/* number */
.summary-number {
    color: #f8fafc;
    font-size: 52px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNCTIONS
# =========================
def extract_json(text):
    match = re.search(r'(\[.*\])', text)
    return match.group(1) if match else None

def map_sim(sim):
    return "Commercial" if sim == "C" else "Registration" if sim == "R" else sim or ""

def extract_tail(text):
    response, status, message = "", "", ""

    m1 = re.search(r'"message"\s*:\s*"([^"]+)"\s*,\s*"statusCode"', text)
    if m1:
        response = m1.group(1)

    m2 = re.search(r'"statusCode"\s*:\s*(\d+)', text)
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

def summary_card(title, total):
    st.markdown(f"""
    <div class="summary-card">
        <div class="summary-title">{title}</div>
        <div class="summary-number">{total}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# UPLOAD
# =========================
col1, col2 = st.columns(2)

with col1:
    file1 = st.file_uploader("DTEN", type=["xlsx", "csv"])

with col2:
    file2 = st.file_uploader("DTENTCAP", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if file1:

    # ===== FILE 1 =====
    df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
    rows1 = process_file(df1)

    df_vin1 = pd.DataFrame(rows1).fillna("")
    df_vin1 = df_vin1.reset_index(drop=True)
    df_vin1.insert(0, "No.", df_vin1.index + 1)

    # ===== FILE 2 =====
    df_vin2 = pd.DataFrame()

    if file2:
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)
        rows2 = process_file(df2)

        df_vin2 = pd.DataFrame(rows2).fillna("")
        df_vin2 = df_vin2.reset_index(drop=True)
        df_vin2.insert(0, "No.", df_vin2.index + 1)

        # 🔥 ตัด columns
        df_vin2 = df_vin2[[
            "No.",
            "UUID",
            "VIN",
            "DeviceID",
            "Response Message",
            "StatusCode"
        ]]

    # =========================
    # SUMMARY
    # =========================
    st.markdown("## Summary")

    cards = []
    cards.append(("DTEN", len(df_vin1)))

    if not df_vin2.empty:
        cards.append(("DTENTCAP", len(df_vin2)))

    cols = st.columns(len(cards))

    for i, (title, total) in enumerate(cards):
        with cols[i]:
            summary_card(title, total)

    # =========================
    # TABLE
    # =========================
    st.markdown("### DTEN")
    st.dataframe(df_vin1, use_container_width=True)

    if not df_vin2.empty:
        st.markdown("### DTENTCAP")
        st.dataframe(df_vin2, use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        df_vin1.to_excel(writer, index=False, sheet_name='DTEN')

        if not df_vin2.empty:
            df_vin2.to_excel(writer, index=False, sheet_name='DTENTCAP')

        # SUMMARY SHEET
        summary_data = []

        summary_data.append({
            "Source": "DTEN",
            "Total": len(df_vin1),
            "Error": 0
        })

        if not df_vin2.empty:
            summary_data.append({
                "Source": "DTENTCAP",
                "Total": len(df_vin2),
                "Error": 0
            })

        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, index=False, sheet_name='Summary')

    output.seek(0)

    st.download_button(
        "Download",
        data=output,
        file_name="dten-summary.xlsx"
    )

else:
    st.info("Please upload DTEN file first")
