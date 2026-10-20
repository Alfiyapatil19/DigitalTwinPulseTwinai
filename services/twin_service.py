from database import get_connection

def get_twin_telemetry_history(patient_id, limit=72):
    """
    Fetches the latest continuous telemetry records for the patient's digital twin.
    Calculates summary metrics: Time-in-Range (TIR), Mean Glucose, Glycemic Variability.
    """
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            # First find twin and paired CGM stream
            cursor.execute("""
                SELECT id, paired_cgm_user_id, target_glucose_min, target_glucose_max, baseline_hba1c
                FROM twin_profiles
                WHERE patient_id = %s;
            """, (patient_id,))
            twin = cursor.fetchone()
            if not twin or not twin['paired_cgm_user_id']:
                return {
                    'twin': twin,
                    'readings': [],
                    'metrics': None
                }

            cgm_user = twin['paired_cgm_user_id']
            min_target = float(twin['target_glucose_min'] or 70.0)
            max_target = float(twin['target_glucose_max'] or 180.0)

            # Retrieve readings ordered chronologically
            query = """
                SELECT 
                    id, cgm_user_id, recorded_at, glucose_level, cgm_quality_flag,
                    insulin_bolus, insulin_basal, carbs, meal_type,
                    exercise_steps, exercise_intensity, heart_rate, skin_temp, gsr,
                    stress_level, sleep_stage
                FROM glucose_readings
                WHERE cgm_user_id = %s
                ORDER BY recorded_at DESC
                LIMIT %s;
            """
            cursor.execute(query, (cgm_user, limit))
            readings = cursor.fetchall()
            # Reverse so it's ascending chronological order for charts
            readings.reverse()

            if not readings:
                return {'twin': twin, 'readings': [], 'metrics': None}

            # Calculate clinical glycemic statistics
            glucose_vals = [float(r['glucose_level']) for r in readings]
            total_count = len(glucose_vals)
            in_range = sum(1 for g in glucose_vals if min_target <= g <= max_target)
            below_range = sum(1 for g in glucose_vals if g < min_target)
            above_range = sum(1 for g in glucose_vals if g > max_target)

            mean_g = sum(glucose_vals) / total_count
            variance = sum((g - mean_g) ** 2 for g in glucose_vals) / total_count
            std_dev = variance ** 0.5
            cv = (std_dev / mean_g) * 100 if mean_g > 0 else 0.0  # Coefficient of variation

            # Glucose Management Indicator (estimated HbA1c from mean glucose)
            gmi = 3.31 + (0.02392 * mean_g)

            metrics = {
                'total_readings': total_count,
                'mean_glucose': round(mean_g, 1),
                'std_dev': round(std_dev, 1),
                'cv_pct': round(cv, 1),
                'time_in_range_pct': round((in_range / total_count) * 100, 1),
                'time_below_range_pct': round((below_range / total_count) * 100, 1),
                'time_above_range_pct': round((above_range / total_count) * 100, 1),
                'estimated_hba1c': round(gmi, 1),
                'target_min': min_target,
                'target_max': max_target
            }

            # Convert datetime to string for clean JSON serialization
            for r in readings:
                if hasattr(r['recorded_at'], 'strftime'):
                    r['recorded_at'] = r['recorded_at'].strftime("%Y-%m-%d %H:%M:%S")

            return {
                'twin': twin,
                'readings': readings,
                'metrics': metrics
            }
    finally:
        conn.close()

def pair_twin_stream(patient_id, cgm_user_id, wearable_subject_id=None):
    """
    Pairs or switches the continuous sensor stream for a patient's twin profile.
    """
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE twin_profiles
                SET paired_cgm_user_id = %s,
                    paired_wearable_subject_id = %s,
                    twin_status = 'active'
                WHERE patient_id = %s;
            """, (cgm_user_id, wearable_subject_id, patient_id))

            cursor.execute("""
                UPDATE glucose_readings g
                JOIN twin_profiles t ON g.cgm_user_id = t.paired_cgm_user_id
                SET g.twin_id = t.id
                WHERE t.patient_id = %s;
            """, (patient_id,))
            conn.commit()
            return True
    finally:
        conn.close()
