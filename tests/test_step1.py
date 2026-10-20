import unittest
import os
import glob
from config import Config
from database import get_connection, init_database
from importers.synthea_importer import parse_synthea_file
import pandas as pd

class TestStep1DatabaseAndIngestion(unittest.TestCase):

    def test_01_config_and_dataset_paths(self):
        """Verify configuration loads properly and dataset files exist."""
        self.assertIsNotNone(Config.DB_USER)
        self.assertIsNotNone(Config.DB_PASSWORD)
        self.assertEqual(Config.DB_NAME, "digital_twin_db")
        self.assertTrue(os.path.exists(Config.SYNTHEA_DIR), f"Synthea directory missing: {Config.SYNTHEA_DIR}")
        self.assertTrue(os.path.exists(Config.GLUCOBENCH_CSV), f"GlucoBench CSV missing: {Config.GLUCOBENCH_CSV}")

    def test_02_mysql_connection(self):
        """Verify that PyMySQL can connect to the MySQL database."""
        conn = get_connection(use_database=False)
        self.assertIsNotNone(conn)
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")
            res = cursor.fetchone()
            self.assertEqual(list(res.values())[0], 1)
        conn.close()

    def test_03_schema_initialization_and_tables(self):
        """Verify that init_database creates all required tables."""
        init_database()
        conn = get_connection(use_database=True)
        expected_tables = {'patients', 'conditions', 'medications', 'twin_profiles', 'glucose_readings'}
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES;")
                tables = {list(row.values())[0] for row in cursor.fetchall()}
                for exp in expected_tables:
                    self.assertIn(exp, tables, f"Expected table '{exp}' not found in database.")
        finally:
            conn.close()

    def test_04_synthea_xml_parser(self):
        """Test parsing of a sample Synthea C-CDA XML file."""
        xml_files = glob.glob(os.path.join(Config.SYNTHEA_DIR, "*.xml"))
        self.assertGreater(len(xml_files), 0, "No Synthea XML files found")
        
        sample_file = xml_files[0]
        patient, conditions, meds = parse_synthea_file(sample_file)
        
        self.assertTrue(patient['patient_uuid'], "Patient UUID should not be empty")
        self.assertTrue(patient['first_name'], "First name should not be empty")
        self.assertTrue(patient['last_name'], "Last name should not be empty")
        self.assertIn(patient['gender'], ['M', 'F', 'UN'])
        self.assertIsInstance(conditions, list)
        self.assertIsInstance(meds, list)
        print(f"\n[Test] Parsed patient: {patient['first_name']} {patient['last_name']}, {len(conditions)} conditions, {len(meds)} meds")

    def test_05_glucobench_csv_integrity(self):
        """Test GlucoBench CSV schema, data types, and values."""
        df = pd.read_csv(Config.GLUCOBENCH_CSV, nrows=50)
        self.assertIn('user_id', df.columns)
        self.assertIn('timestamp', df.columns)
        self.assertIn('glucose', df.columns)
        self.assertGreater(df['glucose'].min(), 20)
        self.assertLess(df['glucose'].max(), 500)

    def test_06_id_independence(self):
        """Verify that Synthea patient UUIDs and GlucoBench user IDs are distinct systems."""
        xml_files = glob.glob(os.path.join(Config.SYNTHEA_DIR, "*.xml"))[:5]
        synthea_uuids = [parse_synthea_file(f)[0]['patient_uuid'] for f in xml_files]
        
        df = pd.read_csv(Config.GLUCOBENCH_CSV, nrows=10)
        cgm_user_ids = df['user_id'].unique().tolist()

        # Confirm there is no overlap between synthetic EHR UUIDs and CGM device user strings
        overlap = set(synthea_uuids).intersection(set(cgm_user_ids))
        self.assertEqual(len(overlap), 0, "Synthea IDs and GlucoBench IDs must not collide")

if __name__ == '__main__':
    unittest.main()
