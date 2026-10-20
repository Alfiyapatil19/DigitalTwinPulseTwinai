import os
import sys
import json
import joblib
import numpy as np

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from ml.feature_pipeline import prepare_inference_vector

class GlucoseTwinPredictor:
    """
    Inference and Clinical Decision Support engine for the Blood Glucose Digital Twin.
    """
    _instance = None

    def __init__(self):
        self.model = None
        self.metadata = None
        self.load_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GlucoseTwinPredictor()
        return cls._instance

    def load_model(self):
        saved_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
        model_path = os.path.join(saved_dir, "glucose_predictor.joblib")
        metadata_path = os.path.join(saved_dir, "model_metadata.json")

        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

    def assess_clinical_risk(self, current_g, predicted_g, delta):
        """
        Evidence-based clinical risk stratification following American Diabetes Association (ADA) guidelines.
        Evaluates both current continuous reading and 30-minute predicted trajectory.
        """
        # 1. Glucose Threshold Alerts (evaluating both current state and predicted state)
        worst_hypo = min(current_g, predicted_g)
        worst_hyper = max(current_g, predicted_g)

        if worst_hypo < 54.0:
            risk = "Critical"
            alert_code = "CRITICAL_HYPOGLYCEMIA"
            alert_msg = f"Level 2 Severe Hypoglycemia Alert (Current: {current_g:.1f}, Predicted: {predicted_g:.1f} mg/dL). Neuroglycopenic symptom risk!"
            recommendation = "Immediate intake of 15-20g rapid-acting carbohydrates (glucose tablets or juice). Recheck in 15 minutes. Prepare glucagon if impaired."
        elif worst_hypo < 70.0:
            risk = "Warning"
            alert_code = "HYPOGLYCEMIA"
            alert_msg = f"Mild Hypoglycemia Alert (Current: {current_g:.1f}, Predicted: {predicted_g:.1f} mg/dL)."
            recommendation = "Rule of 15: Consume 15g fast-acting carbs. Suspend bolus. Re-test glucose in 15 minutes."
        elif worst_hyper > 250.0:
            risk = "Critical"
            alert_code = "CRITICAL_HYPERGLYCEMIA"
            alert_msg = f"Severe Hyperglycemia Alert (Current: {current_g:.1f}, Predicted: {predicted_g:.1f} mg/dL). Ketosis risk."
            recommendation = "Assess for ketones (blood/urine beta-hydroxybutyrate). Calculate correction bolus. Contact clinician if persistent."
        elif worst_hyper > 180.0:
            risk = "Warning"
            alert_code = "HYPERGLYCEMIA"
            alert_msg = f"Hyperglycemia Alert (Current: {current_g:.1f}, Predicted: {predicted_g:.1f} mg/dL)."
            recommendation = "Hydrate with water. Verify active insulin on board (IOB) before administering correction bolus."
        else:
            risk = "Normal"
            alert_code = "IN_TARGET_RANGE"
            alert_msg = f"Glucose stable in ADA Target Range (Current: {current_g:.1f}, Predicted: {predicted_g:.1f} mg/dL)."
            recommendation = "Optimal Time-in-Range (TIR 70-180 mg/dL). Continue standard monitoring schedule."
            recommendation = "Assess for ketones (blood/urine beta-hydroxybutyrate). Calculate correction bolus. Contact clinician if persistent."

        # 2. Trend Velocity Assessment (Rate of Change over 30 min)
        # delta / 30 gives rate in mg/dL per min
        rate_per_min = delta / 30.0
        if rate_per_min >= 2.0:
            trend = "rapidly_rising"
            trend_desc = "Rapidly rising (> 2 mg/dL/min)"
        elif rate_per_min >= 1.0:
            trend = "rising"
            trend_desc = "Rising (1 - 2 mg/dL/min)"
        elif rate_per_min <= -2.0:
            trend = "rapidly_falling"
            trend_desc = "Rapidly dropping (< -2 mg/dL/min) - High Acute Hypo Risk"
        elif rate_per_min <= -1.0:
            trend = "falling"
            trend_desc = "Falling (1 - 2 mg/dL/min)"
        else:
            trend = "stable"
            trend_desc = "Stable trend (-1 to +1 mg/dL/min)"

        return {
            'risk_level': risk,
            'alert_code': alert_code,
            'alert_message': alert_msg,
            'trend_direction': trend,
            'trend_description': trend_desc,
            'rate_per_minute': round(rate_per_min, 2),
            'clinical_recommendation': recommendation
        }

    def predict(self, input_dict):
        """
        Runs machine learning prediction and clinical risk scoring on input sensor data.
        """
        if self.model is None:
            self.load_model()
            if self.model is None:
                raise RuntimeError("ML model artifact not found. Run ml/train_models.py first.")

        # Prepare 19-dimensional feature vector
        feat_vec = prepare_inference_vector(input_dict)
        pred_val = float(self.model.predict(feat_vec)[0])

        current_val = float(input_dict.get('glucose', 110.0))
        delta = pred_val - current_val

        # Risk stratification
        risk_eval = self.assess_clinical_risk(current_val, pred_val, delta)

        # Margin of error from champion model metrics
        rmse = self.metadata.get('champion_metrics', {}).get('rmse', 2.5) if self.metadata else 2.5
        ci_lower = max(20.0, round(pred_val - (1.96 * rmse), 1))
        ci_upper = round(pred_val + (1.96 * rmse), 1)

        return {
            'current_glucose': round(current_val, 1),
            'predicted_glucose_30m': round(pred_val, 1),
            'delta_mg_dl': round(delta, 1),
            'confidence_interval_95': {'lower': ci_lower, 'upper': ci_upper},
            'risk_assessment': risk_eval,
            'champion_model': self.metadata.get('champion_model', 'XGBoost') if self.metadata else 'XGBoost',
            'prediction_horizon': '30 minutes ahead',
            'limitations': self.metadata.get('clinical_limitations', []) if self.metadata else []
        }

# Global helper function
def predict_future_glucose(input_data):
    predictor = GlucoseTwinPredictor.get_instance()
    return predictor.predict(input_data)
