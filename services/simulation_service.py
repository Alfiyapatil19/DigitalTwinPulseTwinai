import datetime
import random
from database import get_connection
from ml.predictor import predict_future_glucose

# Active simulation cursor offsets per patient twin
_STREAM_CURSORS = {}

def get_realtime_stream_tick(patient_id, step_forward=True):
    """
    Simulates real-time sensor ingestion from continuous glucose & wearable telemetry.
    Advances the streaming cursor, runs machine learning prediction, and generates ADA clinical alerts.
    """
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            # 1. Fetch patient twin
            cursor.execute("""
                SELECT t.id, t.patient_id, t.twin_name, t.paired_cgm_user_id,
                       t.paired_wearable_subject_id, t.target_glucose_min, t.target_glucose_max,
                       t.insulin_sensitivity, t.carb_ratio, t.baseline_hba1c,
                       p.first_name, p.last_name, p.gender, p.birth_date
                FROM twin_profiles t
                JOIN patients p ON t.patient_id = p.id
                WHERE t.patient_id = %s;
            """, (patient_id,))
            twin = cursor.fetchone()

            if not twin or not twin['paired_cgm_user_id']:
                return {
                    'status': 'unpaired',
                    'message': 'No continuous monitoring device paired to this patient twin.'
                }

            cgm_user = twin['paired_cgm_user_id']

            # Count total readings for this CGM user
            cursor.execute("SELECT COUNT(*) AS total FROM glucose_readings WHERE cgm_user_id = %s;", (cgm_user,))
            total_readings = cursor.fetchone()['total']

            if total_readings == 0:
                return {'status': 'no_data', 'message': 'No readings found for stream.'}

            # Manage simulation cursor (start dynamically at patient-specific offset in the dataset)
            default_start = ((patient_id * 67) % max(total_readings - 120, 1)) + 30
            cursor_pos = _STREAM_CURSORS.get(patient_id, default_start)
            if step_forward:
                cursor_pos = (cursor_pos + 1) % max(total_readings - 10, 1)
                _STREAM_CURSORS[patient_id] = cursor_pos
            else:
                _STREAM_CURSORS[patient_id] = cursor_pos

            # 2. Fetch current reading and prior readings for lags
            cursor.execute("""
                SELECT * FROM glucose_readings
                WHERE cgm_user_id = %s
                ORDER BY recorded_at ASC
                LIMIT 1 OFFSET %s;
            """, (cgm_user, cursor_pos))
            current = cursor.fetchone()

            # Retrieve prior lags from database or current reading
            prev_cursor = max(0, cursor_pos - 1)
            cursor.execute("""
                SELECT glucose_level FROM glucose_readings
                WHERE cgm_user_id = %s
                ORDER BY recorded_at ASC
                LIMIT 1 OFFSET %s;
            """, (cgm_user, prev_cursor))
            prev_row = cursor.fetchone()
            lag_1 = float(prev_row['glucose_level']) if prev_row else float(current['glucose_level'])

            # 3. Construct input payload for ML model dynamically from dataset row
            g_val = float(current['glucose_level'])
            ml_input = {
                'glucose': g_val,
                'glucose_lag_1': lag_1,
                'glucose_lag_3': float(current.get('glucose_lag_3') or lag_1),
                'glucose_lag_6': float(current.get('glucose_lag_6') or lag_1),
                'glucose_roll_mean_1h': float(current.get('glucose_roll_mean_1h') or g_val),
                'insulin_bolus': float(current.get('insulin_bolus') or 0.0),
                'insulin_basal': float(current.get('insulin_basal') or 1.0),
                'carbs': int(current.get('carbs') or 0),
                'heart_rate': float(current.get('heart_rate') or 75.0),
                'skin_temp': float(current.get('skin_temp') or 36.5),
                'gsr': float(current.get('gsr') or 1.5),
                'stress_level': int(current.get('stress_level') or 1),
                'hbA1c': float(twin.get('baseline_hba1c') or 6.2),
                'carb_ratio': float(twin.get('carb_ratio') or 12.0),
                'insulin_sensitivity': float(twin.get('insulin_sensitivity') or 40.0)
            }

            # 4. Run Machine Learning Prediction & Risk Assessment
            prediction = predict_future_glucose(ml_input)

            # 5. Update twin sync time & risk level in MySQL
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE twin_profiles
                SET last_sync_time = %s,
                    risk_level = %s
                WHERE id = %s;
            """, (now_str, prediction['risk_assessment']['risk_level'].lower(), twin['id']))
            conn.commit()

            # Format timestamp
            rec_at = current['recorded_at'].strftime("%Y-%m-%d %H:%M:%S") if hasattr(current['recorded_at'], 'strftime') else str(current['recorded_at'])

            return {
                'status': 'success',
                'patient_id': patient_id,
                'patient_name': f"{twin['first_name']} {twin['last_name']}",
                'twin_name': twin['twin_name'],
                'cgm_user_id': cgm_user,
                'wearable_id': twin['paired_wearable_subject_id'] or 'E4-W01',
                'recorded_at': rec_at,
                'simulated_clock': now_str,
                'telemetry': {
                    'glucose': g_val,
                    'heart_rate': ml_input['heart_rate'],
                    'skin_temp': ml_input['skin_temp'],
                    'gsr': ml_input['gsr'],
                    'stress_level': ml_input['stress_level'],
                    'insulin_bolus': ml_input['insulin_bolus'],
                    'carbs': ml_input['carbs'],
                    'cgm_quality_flag': int(current.get('cgm_quality_flag') or 1),
                    'cursor_index': cursor_pos,
                    'total_dataset_rows': total_readings,
                    'dataset_source': f"Kaggle GlucoBench ({cgm_user}) + Empatica E4 ({twin['paired_wearable_subject_id'] or 'S01'})"
                },
                'prediction': prediction,
                'ml_input_features': ml_input
            }
    finally:
        conn.close()

def simulate_clinical_event(patient_id, event_type, params):
    """
    Applies what-if clinical interventions to the patient's Digital Twin:
    - MEAL: Ingest carbohydrates (carbs in grams)
    - INSULIN: Administer bolus insulin (units)
    - EXERCISE: Physical activity session (steps, intensity)
    - STRESS: Stress / sympathetic arousal (stress level 0-5)
    """
    # First get the current baseline state
    baseline = get_realtime_stream_tick(patient_id, step_forward=False)
    if baseline.get('status') != 'success':
        return baseline

    telemetry = baseline['telemetry']
    current_g = telemetry['glucose']

    # Apply physiological perturbation based on standard endocrine kinetics
    event_summary = ""
    if event_type == 'MEAL':
        carbs = int(params.get('carbs', 45))
        telemetry['carbs'] = carbs
        # Carb effect: roughly 1g carb raises glucose by 3-4 mg/dL divided by body weight/ICR over 30-60 min
        est_rise = min(carbs * 0.8, 60.0)
        telemetry['glucose'] = round(current_g + (est_rise * 0.4), 1)  # immediate 30-min portion
        event_summary = f"Meal Logged: {carbs}g carbohydrates"

    elif event_type == 'INSULIN':
        units = float(params.get('units', 3.0))
        telemetry['insulin_bolus'] = units
        # Insulin effect: ISF drop
        est_drop = units * 12.0
        telemetry['glucose'] = max(45.0, round(current_g - (est_drop * 0.35), 1))
        event_summary = f"Bolus Administered: {units} Units insulin"

    elif event_type == 'EXERCISE':
        steps = int(params.get('steps', 2500))
        intensity = params.get('intensity', 'medium')
        telemetry['heart_rate'] = 125.0 if intensity == 'high' else 105.0
        telemetry['skin_temp'] = 37.1
        # Moderate exercise enhances glucose clearance
        telemetry['glucose'] = max(55.0, round(current_g - 15.0, 1))
        event_summary = f"Exercise Session: {steps} steps ({intensity} intensity)"

    elif event_type == 'STRESS':
        stress = int(params.get('stress_level', 4))
        telemetry['stress_level'] = stress
        telemetry['gsr'] = 4.8
        telemetry['heart_rate'] = 98.0
        telemetry['glucose'] = round(current_g + (stress * 3.5), 1)
        event_summary = f"Induced Stress Event (Level {stress}/5)"

    # Feed perturbed state through the ML model
    ml_input = {
        'glucose': telemetry['glucose'],
        'glucose_lag_1': current_g,
        'glucose_lag_3': current_g - 2.0,
        'glucose_roll_mean_1h': (telemetry['glucose'] + current_g) / 2.0,
        'insulin_bolus': telemetry.get('insulin_bolus', 0.0),
        'carbs': telemetry.get('carbs', 0),
        'heart_rate': telemetry.get('heart_rate', 75.0),
        'skin_temp': telemetry.get('skin_temp', 36.5),
        'gsr': telemetry.get('gsr', 1.5),
        'stress_level': telemetry.get('stress_level', 1)
    }

    new_prediction = predict_future_glucose(ml_input)

    return {
        'status': 'success',
        'patient_id': patient_id,
        'event_type': event_type,
        'event_summary': event_summary,
        'updated_telemetry': telemetry,
        'new_prediction': new_prediction
    }
