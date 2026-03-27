import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="ITOSE - TCAP 2 FILES", layout="wide")
st.title("ITOSE Tools - TCAP (VIN Focus Version)")

# =========================
# REGEX
# =========================
UUID_REGEX = r'([a-f0-9\-]{36})'
VIN_REGEX = r'"vin"\s*:\s*"([^"]+)"'
DEVICE_REGEX = r'"LDCMID"\s*:\s*"([^"]+)"'
RESULT_REGEX = r'"message"\s*:\s*"([^"]+)"'
SIM_REGEX = r'"simPackage"\s*:\s*"([^"]+)"'

TCAP_REGEX = r'"deviceId":"([^"]+)".*?"IMEI":"([^"]+)".*?"ICCID":"([^"]+)".*?"IMSI":"([^"]+)".*?"prodStatus":"([^"]+)".*?"prodDate":"([^"]+)".*?"sendDate":"([^"]+)".*?"typeStatus":"([^"]+)"'

# =========================
# FUNCTIONS
# =========================
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
    return ['background-color: #ffe6e6' if "success" not in row["Result"].lower() else '' for _ in row]

def highlight_error_tcap(row):
    return ['background-color: #ffe6e6' if row["TypeStatus"] != "OK" else '' for _ in row]

# =========================
# UPLOAD
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
    # 🔥 DATAHUB (VIN LOGIC)
    # =========================
    vin_map = {}

    for col in df_datahub.columns:
        for val in df_datahub[col]:
            if pd.isna(val):
                continue

            text = str(val)

            vin_match = re.search(VIN_REGEX, text)
            if not vin_match:
                continue  # ❌ ไม่มี VIN = ไม่เอา

            vin = vin_match.group(1)

            uuid_match = re.search(UUID_REGEX, text)
            device_match = re.search(DEVICE_REGEX, text)
            result_match = re.search(RESULT_REGEX, text)
            sim_match = re.search(SIM_REGEX, text)

            uuid = uuid_match.group(1) if uuid_match else ""
            device = device_match.group(1) if device_match else ""
            result = result_match.group(1).strip() if result_match else ""
            sim = sim_match.group(1) if sim_match else ""

            # overwrite → เอาตัวล่าสุดต่อ VIN
            vin_map[vin] = {
                "VIN": vin,
                "UUID": uuid,
                "DeviceID": device,
                "Carrier": get_carrier(device),
                "SimPackage": sim,
                "Result": result
            }

    if not vin_map:
        st.error("❌ ไม่พบ VIN ในไฟล์ Datahub (regex อาจไม่ match)")
        st.stop()

    df1 = pd.DataFrame(vin_map.values())

    df1 = df1.reset_index(drop=True)
    df1.insert(0, "No.", df1.index + 1)

    # =========================
    # 🔥 TCAP
    # =========================
    trows = []

    for col in df_tcap.columns:
        for val in df_tcap[col]:
            if pd.isna(val):
                continue

            for d, imei, iccid, imsi, prod, pd1, sd, ts in extract_tcap(str(val)):
                trows.append({
                    "DeviceID": d,
                    "IMEI": imei,
                    "ICCID": iccid,
                    "IMSI": imsi,
                    "ProdStatus": prod,
                    "ProdDate": pd1,
                    "SendDate": sd,
                    "TypeStatus": ts.strip()
                })

    if not trows:
        st.error("❌ ไม่พบข้อมูล TCAP")
        st.stop()

    df2 = pd.DataFrame(trows).drop_duplicates(subset=["DeviceID", "IMEI"])

    df2 = df2.reset_index(drop=True)
    df2.insert(0, "No.", df2.index + 1)

    # =========================
    # COUNT
    # =========================
    datahub_total = len(df1)
    datahub_error = len(df1[~df1["Result"].str.lower().str.contains("success")])

    tcap_total = len(df2)
    tcap_error = len(df2[df2["TypeStatus"] != "OK"])

    # =========================
    # SUMMARY
    # =========================
    st.markdown("### Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Datahub (VIN)", datahub_total)
        st.write(f"Error: {datahub_error}")

    with col2:
        st.metric("TCAP", tcap_total)
        st.write(f"Error: {tcap_error}")

    # =========================
    # TABLE
    # =========================
    st.subheader("TCAPLinkageDatahub (VIN Focus)")
    st.dataframe(df1.style.apply(highlight_error_datahub, axis=1), use_container_width=True)

    st.subheader("TCAPLinkage")
    st.dataframe(df2.style.apply(highlight_error_tcap, axis=1), use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df1.to_excel(writer, index=False, sheet_name='Datahub_VIN')
        df2.to_excel(writer, index=False, sheet_name='TCAP')

    output.seek(0)

    st.download_button(
        "Download Summary",
        data=output,
        file_name="tcap-vin-summary.xlsx"
    )
