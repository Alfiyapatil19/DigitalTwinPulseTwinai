import pymysql
from database import get_connection

def build_twin_profiles():
    """
    Instantiates Digital Twin profiles for Synthea EHR patients.
    Pairs a cohort of patients with continuous monitoring streams (GlucoBench U001-U010
    and Wearable streams S01-S10) without assuming matching IDs.
    """
    conn = get_connection(use_database=True)
    cgm_users = [f"U{i:03d}" for i in range(1, 11)]  # U001 to U010
    wearable_subjects = [f"S{i:02d}" for i in range(1, 11)]  # S01 to S10

    try:
        with conn.cursor() as cursor:
            # 1. Fetch patients
            cursor.execute("SELECT id, first_name, last_name FROM patients ORDER BY id ASC;")
            patients = cursor.fetchall()
            if not patients:
                print("[!] No patients found. Run Synthea import first.")
                return 0

            print(f"[*] Building Digital Twin profiles for {len(patients)} patients...")

            twin_upsert_sql = """
                INSERT INTO twin_profiles (
                    patient_id, twin_name, twin_status, baseline_hba1c,
                    target_glucose_min, target_glucose_max, insulin_sensitivity,
                    carb_ratio, paired_device_type, paired_cgm_user_id,
                    paired_wearable_subject_id, risk_level
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    twin_name = VALUES(twin_name),
                    twin_status = VALUES(twin_status),
                    baseline_hba1c = VALUES(baseline_hba1c),
                    target_glucose_min = VALUES(target_glucose_min),
                    target_glucose_max = VALUES(target_glucose_max),
                    insulin_sensitivity = VALUES(insulin_sensitivity),
                    carb_ratio = VALUES(carb_ratio),
                    paired_device_type = VALUES(paired_device_type),
                    paired_cgm_user_id = VALUES(paired_cgm_user_id),
                    paired_wearable_subject_id = VALUES(paired_wearable_subject_id);
            """

            paired_count = 0
            for idx, p in enumerate(patients):
                patient_id = p['id']
                full_name = f"{p['first_name']} {p['last_name']}"
                twin_name = f"Twin-{p['last_name'].replace(' ', '')}-{patient_id}"

                # Pair ALL patients with real GlucoBench CGM streams U001-U010 and Empatica E4 S01-S10
                stream_idx = idx % len(cgm_users)
                paired_cgm = cgm_users[stream_idx]
                paired_wearable = wearable_subjects[stream_idx]
                status = 'active'
                
                # Clinical metabolic parameters derived from patient index
                hba1c = 5.8 + ((idx % 7) * 0.35)
                isf = 36.0 + ((idx % 8) * 3.0)
                icr = 10.0 + ((idx % 6) * 1.0)
                paired_count += 1

                cursor.execute(twin_upsert_sql, (
                    patient_id, twin_name, status, round(hba1c, 1),
                    70.00, 180.00, round(isf, 1), round(icr, 1),
                    'CGM+Wearable',
                    paired_cgm, paired_wearable, 'normal'
                ))

            conn.commit()

            # 2. Link glucose_readings to twin_profiles for paired streams
            print("[*] Linking glucose readings to active twin profiles...")
            link_sql = """
                UPDATE glucose_readings g
                JOIN twin_profiles t ON g.cgm_user_id = t.paired_cgm_user_id
                SET g.twin_id = t.id
                WHERE t.paired_cgm_user_id IS NOT NULL;
            """
            cursor.execute(link_sql)
            conn.commit()

            print(f"[+] Successfully provisioned {len(patients)} twin profiles ({paired_count} actively paired with CGM & wearable streams).")
            return len(patients)

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    build_twin_profiles()
