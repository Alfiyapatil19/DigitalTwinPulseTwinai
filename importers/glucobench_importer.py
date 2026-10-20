import os
import pandas as pd
import numpy as np
from database import get_connection
from config import Config

def clean_val(val, default=None):
    """
    Cleans pandas / numpy values for safe MySQL insertion (handles NaN, None, inf).
    """
    if pd.isna(val) or val is None:
        return default
    if isinstance(val, (np.floating, float)):
        if np.isneginf(val) or np.isposinf(val):
            return default
        return float(val)
    if isinstance(val, (np.integer, int)):
        return int(val)
    return val

def import_glucobench_data(csv_path=None, batch_size=1000):
    """
    Imports GlucoBench continuous glucose monitoring data into MySQL in batches.
    Guarantees idempotency via UNIQUE KEY (`cgm_user_id`, `recorded_at`).
    """
    csv_path = csv_path or Config.GLUCOBENCH_CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"GlucoBench CSV not found at {csv_path}")

    print(f"[*] Reading GlucoBench CSV from {csv_path}...")
    df = pd.read_csv(csv_path)
    total_rows = len(df)
    print(f"[*] Loaded {total_rows} rows across {df['user_id'].nunique()} unique CGM users.")

    # Validation: Filter rows with valid glucose and timestamp
    df['parsed_timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    valid_mask = (
        df['user_id'].notna() &
        df['parsed_timestamp'].notna() &
        (df['glucose'] > 20) &
        (df['glucose'] < 600)
    )
    invalid_count = total_rows - valid_mask.sum()
    if invalid_count > 0:
        print(f"[!] Warning: Filtered out {invalid_count} invalid or out-of-bounds rows.")
    
    clean_df = df[valid_mask].copy()

    conn = get_connection(use_database=True)
    rows_inserted = 0

    insert_sql = """
        INSERT INTO glucose_readings (
            cgm_user_id, recorded_at, glucose_level, cgm_quality_flag,
            insulin_bolus, insulin_basal, carbs, meal_type,
            exercise_steps, exercise_intensity, heart_rate, skin_temp, gsr,
            sleep_stage, medication_other, stress_level, alcohol, device_id,
            glucose_lag_1, glucose_lag_3, glucose_lag_6, glucose_roll_mean_1h
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            glucose_level = VALUES(glucose_level),
            cgm_quality_flag = VALUES(cgm_quality_flag),
            heart_rate = VALUES(heart_rate),
            skin_temp = VALUES(skin_temp),
            gsr = VALUES(gsr),
            insulin_bolus = VALUES(insulin_bolus),
            carbs = VALUES(carbs);
    """

    try:
        with conn.cursor() as cursor:
            records = []
            for _, row in clean_df.iterrows():
                record = (
                    str(row['user_id']).strip(),
                    row['parsed_timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                    clean_val(row['glucose'], 0.0),
                    int(clean_val(row.get('cgm_quality_flag'), 1)),
                    clean_val(row.get('insulin_bolus'), 0.0),
                    clean_val(row.get('insulin_basal'), 0.0),
                    int(clean_val(row.get('carbs'), 0)),
                    str(clean_val(row.get('meal_type'), 'none')),
                    int(clean_val(row.get('exercise_steps'), 0)),
                    str(clean_val(row.get('exercise_intensity'), 'none')),
                    clean_val(row.get('heart_rate')),
                    clean_val(row.get('skin_temp')),
                    clean_val(row.get('gsr')),
                    str(clean_val(row.get('sleep_stage'), 'awake')),
                    str(clean_val(row.get('medication_other'), 'none')),
                    int(clean_val(row.get('stress_level'), 0)),
                    clean_val(row.get('alcohol'), 0.0),
                    str(clean_val(row.get('device_id'), 'CGM')),
                    clean_val(row.get('glucose_lag_1')),
                    clean_val(row.get('glucose_lag_3')),
                    clean_val(row.get('glucose_lag_6')),
                    clean_val(row.get('glucose_roll_mean_1h'))
                )
                records.append(record)

                if len(records) >= batch_size:
                    cursor.executemany(insert_sql, records)
                    conn.commit()
                    rows_inserted += len(records)
                    print(f"[*] Processed {rows_inserted}/{len(clean_df)} records...")
                    records = []

            # Remaining batch
            if records:
                cursor.executemany(insert_sql, records)
                conn.commit()
                rows_inserted += len(records)
                print(f"[*] Processed {rows_inserted}/{len(clean_df)} records...")

        print(f"[+] GlucoBench import completed successfully. Total processed: {rows_inserted}")
        return rows_inserted
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    import_glucobench_data()
