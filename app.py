import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - B2C", layout="wide")
st.title("ITOSE Tools - B2C")

# =========================
# REGEX
# =========================
PAIR_REGEX = r'"LDCMID":"([A-Za-z0-9\-]+)".*?"StatusReg":"([^"]+)".*?"ResDate":"([^"]+)"'

TCAP_REGEX = r'"deviceId":"([^"]+)".*?"IMEI":"([^"]+)".*?"ICCID":"([^"]+)".*?"IMSI":"([^"]+)".*?"prodStatus":"([^"]+)".*?"prodDate":"([^"]+)".*?"sendDate":"([^"]+)".*?"typeStatus":"([^"]+)"'

# =========================
# FUNCTIONS
# =========================
def extract_pairs(text):
    return re.findall(PAIR_REGEX, text)

def extract_tcap(text):
    return re.findall(TCAP_REGEX, text)

def get_carrier(deviceid):
    if isinstance(deviceid, str) and deviceid.startswith(("A", "Z")):
        return "AIS"
    return "TRUE"

# =========================
# HIGHLIGHT
# =========================
def highlight_error_datahub(row):
    return ['background-color: #ffcccc' if row["Result"] != "Process completed successfully" else '' for _ in row]

def highlight_error_tcap(row):
    return ['background-color: #ffcccc' if row["TypeStatus"] != "OK" else '' for _ in row]

# =========================
# UPLOAD (เหลือ 2 ไฟล์)
# =========================
col1, col2 = st.columns(2)

with col1:
    datahub_file = st.file_uploader("TCAPLinkageDatahub", type=["xlsx", "csv"])

with col2:
    tcap_file = st.file_uploader("TCAPLinkage", type=["xlsx", "csv"])

# =========================
# PROCESS
# =========================
if datahub_file and tcap_file:

    df_datahub = pd.read_csv(datahub_file) if datahub_file.name.endswith(".csv") else pd.read_excel(datahub_file)
    df_tcap = pd.read_csv(tcap_file) if tcap_file.name.endswith(".csv") else pd.read_excel(tcap_file)

    # =========================
    # TCAPLinkageDatahub
    # =========================
    rows = []

    for col in df_datahub.columns:
        for val in df_datahub[col]:
            if pd.isna(val): continue

            for d, s, dt in extract_pairs(str(val)):
                rows.append({
                    "DeviceID": d,
                    "Result": s,
                    "Date Time": dt
                })

    df1 = pd.DataFrame(rows).drop_duplicates()
    df1["Result"] = df1["Result"].astype(str).str.strip()
    df1["Carrier"] = df1["DeviceID"].apply(get_carrier)

    df1 = df1.reset_index(drop=True)
    df1.insert(0, "No.", df1.index + 1)

    # =========================
    # TCAPLinkage
    # =========================
    trows = []

    for col in df_tcap.columns:
        for val in df_tcap[col]:
            if pd.isna(val): continue

            for d, imei, iccid, imsi, prod, pd1, sd, ts in extract_tcap(str(val)):
                trows.append({
                    "DeviceID": d,
                    "IMEI": imei,
                    "ICCID": iccid,
                    "IMSI": imsi,
                    "ProdStatus": prod,
                    "ProdDate": pd1,
                    "SendDate": sd,
                    "TypeStatus": ts
                })

    df2 = pd.DataFrame(trows).drop_duplicates(subset=["DeviceID","IMEI"])
    df2["TypeStatus"] = df2["TypeStatus"].astype(str).str.strip()

    df2 = df2.reset_index(drop=True)
    df2.insert(0, "No.", df2.index + 1)

    # =========================
    # COUNT
    # =========================
    datahub_total = len(df1)
    datahub_error = len(df1[df1["Result"] != "Process completed successfully"])

    tcap_total = len(df2)
    tcap_error = len(df2[df2["TypeStatus"] != "OK"])

    # =========================
    # SUMMARY
    # =========================
    st.markdown("### Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("TCAPLinkageDatahub", datahub_total)
        st.write(f"Error: {datahub_error}")

    with col2:
        st.metric("TCAPLinkage", tcap_total)
        st.write(f"Error: {tcap_error}")

    # =========================
    # TABLE
    # =========================
    st.subheader("TCAPLinkageDatahub")
    st.dataframe(df1.style.apply(highlight_error_datahub, axis=1))

    st.subheader("TCAPLinkage")
    st.dataframe(df2.style.apply(highlight_error_tcap, axis=1))

    # =========================
    # EXPORT (เหลือ 2 Sheet)
    # =========================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df1.to_excel(writer, index=False, sheet_name='TCAPLinkageDatahub')
        df2.to_excel(writer, index=False, sheet_name='TCAPLinkage')

    output.seek(0)

    st.download_button(
        "Download Summary",
        data=output,
        file_name="tcap-summary.xlsx"
    )
