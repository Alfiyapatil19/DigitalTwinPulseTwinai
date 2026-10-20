import unittest
import json
from app import create_app

class TestStep3FlaskBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_01_health_endpoint(self):
        """Test health check route."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')

    def test_02_dashboard_html_render(self):
        """Test main doctor dashboard HTML rendering."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'PULSE-TWIN', resp.data)
        self.assertIn(b'Digital Twin', resp.data)

    def test_03_api_patients_list(self):
        """Test GET /api/patients returns list of patients."""
        resp = self.client.get('/api/patients?limit=10')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['count'], 0)
        self.assertIn('first_name', data['patients'][0])

    def test_04_api_patient_detail(self):
        """Test GET /api/patients/<id> returns complete EHR record with conditions and meds."""
        resp = self.client.get('/api/patients/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        p = data['patient']
        self.assertEqual(p['id'], 1)
        self.assertIn('conditions', p)
        self.assertIn('medications', p)
        self.assertGreater(len(p['conditions']), 0)
        print(f"\n[Test API] Patient 1: {p['first_name']} {p['last_name']}, {len(p['conditions'])} conditions, {len(p['medications'])} meds")

    def test_05_api_twin_telemetry(self):
        """Test GET /api/twins/<id>/telemetry returns historical CGM readings and glycemic metrics."""
        resp = self.client.get('/api/twins/1/telemetry?limit=24')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        t_data = data['data']
        self.assertIn('readings', t_data)
        self.assertIn('metrics', t_data)
        self.assertGreater(len(t_data['readings']), 0)
        self.assertIn('time_in_range_pct', t_data['metrics'])
        print(f"[Test API] Telemetry metrics: TIR={t_data['metrics']['time_in_range_pct']}%, Mean Glucose={t_data['metrics']['mean_glucose']} mg/dL")

    def test_06_api_twin_tick_ml_inference(self):
        """Test GET /api/twins/<id>/tick runs real ML prediction and ADA risk assessment."""
        resp = self.client.get('/api/twins/1/tick?step=false')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        tick = data['data']
        self.assertIn('telemetry', tick)
        self.assertIn('prediction', tick)
        pred = tick['prediction']
        self.assertIn('predicted_glucose_30m', pred)
        self.assertIn('risk_assessment', pred)
        print(f"[Test API] Live Tick: Current={tick['telemetry']['glucose']} -> Pred 30m={pred['predicted_glucose_30m']} mg/dL ({pred['risk_assessment']['risk_level']})")

    def test_07_api_simulate_event(self):
        """Test POST /api/twins/<id>/simulate-event what-if intervention on the twin."""
        payload = {
            'event_type': 'MEAL',
            'params': {'carbs': 50}
        }
        resp = self.client.post('/api/twins/1/simulate-event', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        res = data['result']
        self.assertIn('Meal Logged', res['event_summary'])
        self.assertIn('new_prediction', res)
        print(f"[Test API] Sandbox Meal Event: {res['event_summary']} -> Predicted 30m: {res['new_prediction']['predicted_glucose_30m']} mg/dL")

    def test_08_api_model_info_and_overview(self):
        """Test GET /api/analytics/model-info and /api/analytics/overview."""
        resp = self.client.get('/api/analytics/model-info')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('champion_model', data['metadata'])
        self.assertIn('clinical_limitations', data['metadata'])

        resp2 = self.client.get('/api/analytics/overview')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertGreater(data2['overview']['total_patients'], 0)

if __name__ == '__main__':
    unittest.main()
