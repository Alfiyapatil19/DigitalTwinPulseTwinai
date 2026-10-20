import argparse
import sys
import time
from database import init_database, get_table_counts, get_connection
from importers.synthea_importer import import_synthea_data
from importers.glucobench_importer import import_glucobench_data
from importers.twin_builder import build_twin_profiles

def verify_data():
    """
    Runs verification queries and prints summaries of ingested data.
    """
    print("\n" + "=" * 60)
    print("           DATABASE VERIFICATION REPORT")
    print("=" * 60)

    counts = get_table_counts()
    for table, count in counts.items():
        print(f"  [*] {table:<20}: {count:>8} records")
    print("-" * 60)

    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            # Sample patient
            cursor.execute("SELECT id, first_name, last_name, gender, birth_date, city, state FROM patients LIMIT 3;")
            patients = cursor.fetchall()
            print("\n[+] Sample Patients (from Synthea):")
            for p in patients:
                print(f"    - ID {p['id']}: {p['first_name']} {p['last_name']} ({p['gender']}, DOB: {p['birth_date']}) - {p['city']}, {p['state']}")

            # Sample conditions
            cursor.execute("""
                SELECT c.display_name, c.code, COUNT(*) as patient_count 
                FROM conditions c 
                GROUP BY c.display_name, c.code 
                ORDER BY patient_count DESC 
                LIMIT 5;
            """)
            conds = cursor.fetchall()
            print("\n[+] Top 5 Clinical Conditions:")
            for c in conds:
                print(f"    - {c['display_name']} [SNOMED: {c['code']}]: {c['patient_count']} patients")

            # Sample Digital Twin Profiles
            cursor.execute("""
                SELECT t.id, t.twin_name, t.twin_status, t.paired_cgm_user_id, t.baseline_hba1c,
                       p.first_name, p.last_name
                FROM twin_profiles t
                JOIN patients p ON t.patient_id = p.id
                WHERE t.paired_cgm_user_id IS NOT NULL
                LIMIT 5;
            """)
            twins = cursor.fetchall()
            print("\n[+] Sample Active Digital Twin Pairings:")
            for tw in twins:
                print(f"    - {tw['twin_name']} for {tw['first_name']} {tw['last_name']}: Status={tw['twin_status']}, Paired CGM={tw['paired_cgm_user_id']}, HbA1c={tw['baseline_hba1c']}%")

            # Glucose stream stats
            cursor.execute("""
                SELECT cgm_user_id, COUNT(*) as reading_count, 
                       MIN(glucose_level) as min_g, MAX(glucose_level) as max_g, 
                       AVG(glucose_level) as avg_g
                FROM glucose_readings
                GROUP BY cgm_user_id
                ORDER BY cgm_user_id ASC;
            """)
            cgm_stats = cursor.fetchall()
            print(f"\n[+] CGM Streams Ingested ({len(cgm_stats)} streams):")
            for s in cgm_stats[:5]:
                print(f"    - CGM {s['cgm_user_id']}: {s['reading_count']} readings | Glucose: {s['min_g']:.1f} - {s['max_g']:.1f} mg/dL (mean: {s['avg_g']:.1f})")
            if len(cgm_stats) > 5:
                print(f"    ... and {len(cgm_stats) - 5} more CGM streams.")

    finally:
        conn.close()
    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Digital Twin Data Ingestion Pipeline")
    parser.add_argument("--init-db", action="store_true", help="Initialize MySQL database schema")
    parser.add_argument("--synthea", action="store_true", help="Import Synthea C-CDA XML files")
    parser.add_argument("--glucobench", action="store_true", help="Import GlucoBench CGM CSV dataset")
    parser.add_argument("--twin", action="store_true", help="Build and pair Digital Twin profiles")
    parser.add_argument("--all", action="store_true", help="Run full pipeline (init-db, synthea, glucobench, twin, verify)")
    parser.add_argument("--verify", action="store_true", help="Verify database tables and display stats")
    parser.add_argument("--limit-synthea", type=int, default=None, help="Limit number of Synthea files to import")

    args = parser.parse_args()

    # If no flags provided, default to --all
    if not any([args.init_db, args.synthea, args.glucobench, args.twin, args.all, args.verify]):
        args.all = True

    start_time = time.time()

    if args.all or args.init_db:
        print("\n>>> Step 1.1: Initializing Database Schema...")
        init_database()

    if args.all or args.synthea:
        print("\n>>> Step 1.2: Ingesting Synthea C-CDA XML Records...")
        import_synthea_data(limit=args.limit_synthea)

    if args.all or args.glucobench:
        print("\n>>> Step 1.3: Ingesting GlucoBench Continuous Glucose Readings...")
        import_glucobench_data()

    if args.all or args.twin:
        print("\n>>> Step 1.4: Building Digital Twin Profiles & Stream Pairings...")
        build_twin_profiles()

    if args.all or args.verify:
        print("\n>>> Step 1.5: Verifying Ingested Data...")
        verify_data()

    elapsed = round(time.time() - start_time, 2)
    print(f"[+] Pipeline execution finished in {elapsed}s.")

if __name__ == "__main__":
    main()
