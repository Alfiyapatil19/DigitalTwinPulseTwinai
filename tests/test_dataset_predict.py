import os
import sys
from database import get_connection
from ml.predictor import predict_future_glucose

conn = get_connection(use_database=True)
try:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM glucose_readings WHERE cgm_user_id = 'U001' ORDER BY recorded_at LIMIT 15;")
        rows = cur.fetchall()
        r = rows[5]
        fut = rows[7]  # ~30 min later
        ml_input = {
            'glucose': float(r['glucose_level']),
            'glucose_lag_1': float(r.get('glucose_lag_1') or r['glucose_level']),
            'glucose_lag_3': float(r.get('glucose_lag_3') or r['glucose_level']),
            'glucose_lag_6': float(r.get('glucose_lag_6') or r['glucose_level']),
            'glucose_roll_mean_1h': float(r.get('glucose_roll_mean_1h') or r['glucose_level']),
            'heart_rate': float(r.get('heart_rate') or 75.0),
            'skin_temp': float(r.get('skin_temp') or 36.5),
            'gsr': float(r.get('gsr') or 1.5),
            'stress_level': int(r.get('stress_level') or 1),
            'insulin_bolus': float(r.get('insulin_bolus') or 0.0),
            'carbs': int(r.get('carbs') or 0)
        }
        pred = predict_future_glucose(ml_input)
        actual_future = float(fut['glucose_level'])
        print(f"Current Glucose (t=0): {ml_input['glucose']} mg/dL")
        print(f"Actual Ground Truth from Dataset (t+30m): {actual_future} mg/dL")
        print(f"Model Predicted Output (t+30m): {pred['predicted_glucose_30m']} mg/dL")
        print(f"Residual Error: {abs(pred['predicted_glucose_30m'] - actual_future):.2f} mg/dL")
        print(f"ADA Risk: {pred['risk_assessment']['risk_level']} - {pred['risk_assessment']['alert_code']}")
finally:
    conn.close()
