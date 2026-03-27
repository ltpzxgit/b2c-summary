def process_file(df, mode="datahub"):
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

                # 🔥 TCAP เท่านั้นที่ filter response ว่าง
                if mode == "tcap" and response == "":
                    continue

                if isinstance(data, list):
                    for item in data:

                        vin = item.get("vin", "")
                        if not vin:
                            continue

                        device = item.get("deviceId", "")
                        carrier = item.get("carrier", "")
                        sim = map_sim(item.get("simPackage", ""))

                        # ------------------------
                        # DATAHUB (FULL)
                        # ------------------------
                        if mode == "datahub":
                            rows.append({
                                "UUID": uuid,
                                "VIN": vin,
                                "DeviceID": device,
                                "Carrier": carrier,
                                "SimPackage": sim,
                                "Response Message": response,
                                "StatusCode": status,
                                "Message": msg
                            })

                        # ------------------------
                        # TCAP (CUT COLUMNS)
                        # ------------------------
                        elif mode == "tcap":
                            rows.append({
                                "UUID": uuid,
                                "VIN": vin,
                                "DeviceID": device,
                                "Response Message": response,
                                "StatusCode": status
                            })

            except:
                continue

    return rows
