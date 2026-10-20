import numpy as np
import pandas as pd

FEATURE_NAMES = [
    'glucose',
    'glucose_lag_1',
    'glucose_lag_3',
    'glucose_lag_6',
    'glucose_roll_mean_1h',
    'glucose_velocity',
    'glucose_accel',
    'insulin_bolus',
    'insulin_basal',
    'carbs',
    'heart_rate',
    'skin_temp',
    'gsr',
    'stress_level',
    'hbA1c',
    'age',
    'weight',
    'carb_ratio',
    'insulin_sensitivity'
]

# Clinical defaults for single-sample inference if optional parameters are omitted
CLINICAL_DEFAULTS = {
    'glucose': 110.0,
    'glucose_lag_1': 110.0,
    'glucose_lag_3': 110.0,
    'glucose_lag_6': 110.0,
    'glucose_roll_mean_1h': 110.0,
    'glucose_velocity': 0.0,
    'glucose_accel': 0.0,
    'insulin_bolus': 0.0,
    'insulin_basal': 1.0,
    'carbs': 0.0,
    'heart_rate': 75.0,
    'skin_temp': 36.5,
    'gsr': 1.5,
    'stress_level': 1.0,
    'hbA1c': 6.2,
    'age': 45.0,
    'weight': 75.0,
    'carb_ratio': 12.0,
    'insulin_sensitivity': 40.0
}

def engineer_features(df, is_training=True):
    """
    Computes derived temporal features: velocity, acceleration, and imputed rolling values.
    If is_training=True, also computes future_glucose_30m target.
    """
    data = df.copy()

    # Sort if user_id and timestamp exist
    if 'user_id' in data.columns and 'timestamp' in data.columns:
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data = data.sort_values(by=['user_id', 'timestamp']).reset_index(drop=True)

    # Impute lags if missing
    if 'glucose_lag_1' not in data.columns or data['glucose_lag_1'].isnull().any():
        data['glucose_lag_1'] = data.groupby('user_id')['glucose'].shift(1) if 'user_id' in data.columns else data['glucose'].shift(1)
        data['glucose_lag_1'] = data['glucose_lag_1'].fillna(data['glucose'])

    if 'glucose_lag_3' not in data.columns or data['glucose_lag_3'].isnull().any():
        data['glucose_lag_3'] = data.groupby('user_id')['glucose'].shift(3) if 'user_id' in data.columns else data['glucose'].shift(3)
        data['glucose_lag_3'] = data['glucose_lag_3'].fillna(data['glucose_lag_1'])

    if 'glucose_lag_6' not in data.columns or data['glucose_lag_6'].isnull().any():
        data['glucose_lag_6'] = data.groupby('user_id')['glucose'].shift(6) if 'user_id' in data.columns else data['glucose'].shift(6)
        data['glucose_lag_6'] = data['glucose_lag_6'].fillna(data['glucose_lag_3'])

    if 'glucose_roll_mean_1h' not in data.columns or data['glucose_roll_mean_1h'].isnull().any():
        data['glucose_roll_mean_1h'] = (data['glucose'] + data['glucose_lag_1'] + data['glucose_lag_3']) / 3.0

    # Rate of change (velocity: mg/dL per step)
    data['glucose_velocity'] = data['glucose'] - data['glucose_lag_1']

    # Acceleration (change in velocity)
    prev_velocity = data['glucose_lag_1'] - data['glucose_lag_3']
    data['glucose_accel'] = data['glucose_velocity'] - prev_velocity

    # Handle remaining numerical columns
    for f in FEATURE_NAMES:
        if f not in data.columns:
            data[f] = CLINICAL_DEFAULTS.get(f, 0.0)
        else:
            data[f] = pd.to_numeric(data[f], errors='coerce').fillna(CLINICAL_DEFAULTS.get(f, 0.0))

    if is_training:
        if 'user_id' in data.columns:
            data['future_glucose_30m'] = data.groupby('user_id')['glucose'].shift(-3)
        else:
            data['future_glucose_30m'] = data['glucose'].shift(-3)

    return data

def prepare_inference_vector(input_dict):
    """
    Transforms a dictionary of real-time sensor and patient values into a 2D numpy array
    matching exact FEATURE_NAMES.
    """
    values = []
    g = float(input_dict.get('glucose', CLINICAL_DEFAULTS['glucose']))
    g_lag1 = float(input_dict.get('glucose_lag_1', g))
    g_lag3 = float(input_dict.get('glucose_lag_3', g_lag1))
    g_lag6 = float(input_dict.get('glucose_lag_6', g_lag3))
    roll_1h = float(input_dict.get('glucose_roll_mean_1h', (g + g_lag1 + g_lag3) / 3.0))

    vel = float(input_dict.get('glucose_velocity', g - g_lag1))
    accel = float(input_dict.get('glucose_accel', vel - (g_lag1 - g_lag3)))

    for feature in FEATURE_NAMES:
        if feature == 'glucose':
            val = g
        elif feature == 'glucose_lag_1':
            val = g_lag1
        elif feature == 'glucose_lag_3':
            val = g_lag3
        elif feature == 'glucose_lag_6':
            val = g_lag6
        elif feature == 'glucose_roll_mean_1h':
            val = roll_1h
        elif feature == 'glucose_velocity':
            val = vel
        elif feature == 'glucose_accel':
            val = accel
        else:
            val = float(input_dict.get(feature, CLINICAL_DEFAULTS.get(feature, 0.0)))
        values.append(val)

    return np.array([values], dtype=np.float32)
