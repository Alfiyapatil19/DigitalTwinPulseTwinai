import os
import json
import numpy as np
import pandas as pd
import joblib
import sys
from datetime import datetime

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from config import Config
from ml.feature_pipeline import engineer_features, FEATURE_NAMES

def evaluate_clarke_zones(y_true, y_pred):
    """
    Evaluates clinical accuracy inspired by the Clarke Error Grid:
    - Zone A: Clinically accurate (within 20% or within 20 mg/dL if reference <= 70)
    - Zone B: Benign errors that would not lead to inappropriate treatment
    - Zone C/D/E: Clinically unacceptable errors
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    abs_diff = np.abs(y_true - y_pred)
    pct_err = abs_diff / np.maximum(y_true, 1e-5)

    # Zone A condition
    zone_a = (pct_err <= 0.20) | ((y_true <= 70) & (abs_diff <= 20))
    
    # Zone B condition: benign errors (between 20% and 40%, but not opposite extremes)
    hypo_crit = (y_true < 70) & (y_pred >= 180)  # Failure to detect hypoglycemia (Zone C/D)
    hyper_crit = (y_true > 250) & (y_pred <= 70) # Failure to detect hyperglycemia (Zone C/D)
    dangerous = hypo_crit | hyper_crit

    zone_b = (~zone_a) & (~dangerous) & (pct_err <= 0.40)
    zone_other = (~zone_a) & (~zone_b)

    return {
        'zone_a_pct': float(np.mean(zone_a) * 100),
        'zone_b_pct': float(np.mean(zone_b) * 100),
        'clinically_acceptable_pct': float(np.mean(zone_a | zone_b) * 100),
        'unacceptable_pct': float(np.mean(zone_other) * 100)
    }

def train_and_evaluate():
    """
    Trains multiple models, benchmarks them on unseen patient subjects,
    and serializes the champion model and metadata.
    """
    print("[*] Starting Machine Learning Training Pipeline for Blood Glucose Digital Twin...")
    csv_path = Config.GLUCOBENCH_CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"GlucoBench CSV not found at {csv_path}")

    raw_df = pd.read_csv(csv_path)
    print(f"[*] Loaded raw dataset: {raw_df.shape[0]} rows, {raw_df['user_id'].nunique()} subjects.")

    # 1. Feature Engineering
    engineered_df = engineer_features(raw_df, is_training=True)
    clean_df = engineered_df.dropna(subset=['future_glucose_30m']).copy()
    print(f"[*] Post-engineering clean dataset: {clean_df.shape[0]} rows.")

    X = clean_df[FEATURE_NAMES]
    y = clean_df['future_glucose_30m']

    # 2. Patient-based split: Train on U001-U008, Evaluate on Unseen Cohort U009-U010
    train_mask = clean_df['user_id'].isin([f'U00{i}' for i in range(1, 9)])
    test_mask = clean_df['user_id'].isin(['U009', 'U010'])

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    print(f"[*] Training cohort (U001-U008): {X_train.shape[0]} samples")
    print(f"[*] Unseen test cohort (U009-U010): {X_test.shape[0]} samples")

    # 3. Models dictionary
    models = {
        'Ridge_Regression': Ridge(alpha=1.0),
        'Random_Forest': RandomForestRegressor(
            n_estimators=60, max_depth=12, random_state=42, n_jobs=-1
        ),
        'XGBoost': xgb.XGBRegressor(
            n_estimators=120, max_depth=5, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85, random_state=42
        )
    }

    results = {}
    best_rmse = float('inf')
    champion_name = None
    champion_model = None

    print("\n" + "=" * 78)
    print(f"{'Model':<18} | {'RMSE (mg/dL)':<13} | {'MAE (mg/dL)':<12} | {'MAPE (%)':<9} | {'R2':<7} | {'Zone A+B (%)'}")
    print("=" * 78)

    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae = float(mean_absolute_error(y_test, preds))
        mape = float(np.mean(np.abs((y_test - preds) / y_test)) * 100)
        r2 = float(r2_score(y_test, preds))
        clarke = evaluate_clarke_zones(y_test, preds)

        results[name] = {
            'rmse': round(rmse, 4),
            'mae': round(mae, 4),
            'mape': round(mape, 2),
            'r2': round(r2, 4),
            'clarke': clarke
        }

        print(f"{name:<18} | {rmse:<13.3f} | {mae:<12.3f} | {mape:<9.2f} | {r2:<7.4f} | {clarke['clinically_acceptable_pct']:.2f}%")

        if rmse < best_rmse:
            best_rmse = rmse
            champion_name = name
            champion_model = model

    print("=" * 78)
    print(f"[+] Champion Model Selected: {champion_name} (RMSE = {best_rmse:.3f} mg/dL)")

    # 4. Feature Importance Extraction
    if hasattr(champion_model, 'feature_importances_'):
        importances = dict(zip(FEATURE_NAMES, [float(x) for x in champion_model.feature_importances_]))
        sorted_importance = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))
    elif hasattr(champion_model, 'coef_'):
        importances = dict(zip(FEATURE_NAMES, [float(abs(x)) for x in champion_model.coef_]))
        sorted_importance = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))
    else:
        sorted_importance = {}

    print("\n[+] Top 5 Influential Predictive Features:")
    for f_name, f_val in list(sorted_importance.items())[:5]:
        print(f"    - {f_name}: {f_val:.4f}")

    # 5. Save Artifacts
    saved_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
    os.makedirs(saved_dir, exist_ok=True)

    model_path = os.path.join(saved_dir, "glucose_predictor.joblib")
    joblib.dump(champion_model, model_path)
    print(f"\n[+] Champion model saved to {model_path}")

    metadata = {
        'champion_model': champion_name,
        'trained_at': datetime.now().isoformat(),
        'prediction_horizon': '30 minutes ahead',
        'train_samples': int(X_train.shape[0]),
        'test_samples': int(X_test.shape[0]),
        'features': FEATURE_NAMES,
        'feature_importance': sorted_importance,
        'model_comparison': results,
        'champion_metrics': results[champion_name],
        'clinical_limitations': [
            "Physiological sensor lag: Interstitial CGM readings lag capillary blood glucose by 5-15 minutes.",
            "Unannounced dietary intake: Carbohydrate consumption not logged in real-time may result in unpredicted postprandial spikes.",
            "Variable insulin pharmacokinetics: Absorption rates can vary with injection site temperature, lipohypertrophy, and exercise.",
            "Circadian & illness variability: Acute stress, infection, or sleep deprivation alter insulin sensitivity dynamically.",
            "Generalization threshold: Predictions for values far outside [40, 400] mg/dL require clinical fingerstick verification."
        ]
    }

    metadata_path = os.path.join(saved_dir, "model_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Model metadata and clinical limitations saved to {metadata_path}")

    return metadata

if __name__ == "__main__":
    train_and_evaluate()
