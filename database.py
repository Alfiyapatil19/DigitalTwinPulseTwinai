import os
import pymysql
from pymysql.constants import CLIENT
from config import Config

def get_connection(use_database=True):
    """
    Creates and returns a PyMySQL database connection.
    If use_database is False, connects to MySQL server without selecting a specific database.
    """
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME if use_database else None,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        client_flag=CLIENT.MULTI_STATEMENTS
    )

def init_database():
    """
    Initializes the database and executes schema.sql to create all required tables.
    """
    print(f"[*] Connecting to MySQL at {Config.DB_HOST}:{Config.DB_PORT} as {Config.DB_USER}...")
    
    # 1. Connect without selecting database to create DB if needed
    conn = get_connection(use_database=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        print(f"[+] Database '{Config.DB_NAME}' ensured.")
    finally:
        conn.close()

    # 2. Connect to the database and execute schema.sql
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            # Execute schema statements
            cursor.execute(schema_sql)
        conn.commit()
        print("[+] All database tables (`patients`, `conditions`, `medications`, `twin_profiles`, `glucose_readings`) initialized successfully.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_table_counts():
    """
    Returns row counts for all core tables in digital_twin_db.
    """
    tables = ['patients', 'conditions', 'medications', 'twin_profiles', 'glucose_readings']
    counts = {}
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            for tbl in tables:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{tbl}`;")
                row = cursor.fetchone()
                counts[tbl] = row['cnt']
        return counts
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
    counts = get_table_counts()
    print("[*] Current Table Row Counts:", counts)
