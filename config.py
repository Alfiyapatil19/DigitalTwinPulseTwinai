import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "digital_twin_db")
    
    SECRET_KEY = os.getenv("SECRET_KEY", "digital_twin_secret_2026")
    
    # Dataset locations
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SYNTHEA_DIR = os.path.join(BASE_DIR, "synthea_sample_data_ccda_latest")
    GLUCOBENCH_CSV = os.path.join(BASE_DIR, "archive (3)", "GlucoBench_benchmark_dataset.csv")
    WEARABLE_DIR = os.path.join(BASE_DIR, "archive (4)", "wearable-device-dataset-from-induced-stress-and-structured-exercise-sessions-1.0.1")

    @classmethod
    def get_db_url(cls):
        return f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
