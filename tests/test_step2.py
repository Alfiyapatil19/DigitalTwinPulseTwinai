import unittest
import os
import json
from ml.predictor import GlucoseTwinPredictor, predict_future_glucose
from ml.feature_pipeline import FEATURE_NAMES, prepare_inference_vector

class TestStep2MachineLearning(unittest.TestCase):

    def setUp(self):
        self.predictor = GlucoseTwinPredictor.get_instance()

    def test_01_model_and_metadata_artifacts_exist(self):
        """Verify model artifact and metadata JSON exist on disk."""
        saved_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "saved_models")
        model_path = os.path.join(saved_dir, "glucose_predictor.joblib")
        metadata_path = os.path.join(saved_dir, "model_metadata.json")

        self.assertTrue(os.path.exists(model_path), f"Missing model artifact: {model_path}")
        self.assertTrue(os.path.exists(metadata_path), f"Missing metadata: {metadata_path}")

        with open(metadata_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        self.assertIn('champion_model', meta)
        self.assertIn('champion_metrics', meta)
        self.assertIn('clinical_limitations', meta)
        self.assertGreater(len(meta['clinical_limitations']), 0)

    def test_02_feature_vector_dimension(self):
        """Verify feature engineering produces exact 19-dimensional vector."""
        sample_input = {
            'glucose': 125.0,
            'glucose_lag_1': 120.0,
            'heart_rate': 78.0,
            'insulin_bolus': 2.5
        }
        vec = prepare_inference_vector(sample_input)
        self.assertEqual(vec.shape, (1, 19))
        self.assertEqual(len(FEATURE_NAMES), 19)

    def test_03_inference_normal_range(self):
        """Test inference for a patient in normal target range."""
        result = predict_future_glucose({
            'glucose': 110.0,
            'glucose_lag_1': 108.0,
            'glucose_lag_3': 105.0,
            'heart_rate': 72.0,
            'insulin_basal': 1.0,
            'carbs': 0
        })

        self.assertIn('predicted_glucose_30m', result)
        self.assertIn('confidence_interval_95', result)
        self.assertIn('risk_assessment', result)
        self.assertEqual(result['risk_assessment']['risk_level'], 'Normal')
        self.assertEqual(result['risk_assessment']['alert_code'], 'IN_TARGET_RANGE')
        print(f"\n[Test Normal] Predicted: {result['predicted_glucose_30m']} mg/dL | Risk: {result['risk_assessment']['risk_level']}")

    def test_04_inference_hypoglycemia_alert(self):
        """Test clinical alert triggering for low glucose (< 70 mg/dL)."""
        result = predict_future_glucose({
            'glucose': 65.0,
            'glucose_lag_1': 72.0,
            'glucose_lag_3': 80.0,
            'heart_rate': 85.0
        })
        self.assertIn(result['risk_assessment']['risk_level'], ['Warning', 'Critical'])
        self.assertIn('HYPOGLYCEMIA', result['risk_assessment']['alert_code'])
        print(f"[Test Hypo] Predicted: {result['predicted_glucose_30m']} mg/dL | Alert: {result['risk_assessment']['alert_code']}")

    def test_05_inference_hyperglycemia_alert(self):
        """Test clinical alert triggering for high glucose (> 180 mg/dL)."""
        result = predict_future_glucose({
            'glucose': 220.0,
            'glucose_lag_1': 210.0,
            'glucose_lag_3': 195.0,
            'heart_rate': 90.0
        })
        self.assertIn(result['risk_assessment']['risk_level'], ['Warning', 'Critical'])
        self.assertIn('HYPERGLYCEMIA', result['risk_assessment']['alert_code'])
        print(f"[Test Hyper] Predicted: {result['predicted_glucose_30m']} mg/dL | Alert: {result['risk_assessment']['alert_code']}")

    def test_06_model_performance_benchmarks(self):
        """Ensure champion model meets strict clinical benchmark thresholds."""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "saved_models", "model_metadata.json")) as f:
            meta = json.load(f)
        metrics = meta['champion_metrics']
        # RMSE should be under 15 mg/dL (clinical standard for CGM 30-min horizon)
        self.assertLess(metrics['rmse'], 15.0)
        # R2 should be positive and high
        self.assertGreater(metrics['r2'], 0.80)
        # Clarke Zone A+B should be >= 95%
        self.assertGreaterEqual(metrics['clarke']['clinically_acceptable_pct'], 95.0)

if __name__ == '__main__':
    unittest.main()
