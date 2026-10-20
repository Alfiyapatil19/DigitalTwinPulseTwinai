import datetime
from database import get_connection

def calculate_age(birth_date):
    if not birth_date:
        return None
    if isinstance(birth_date, str):
        try:
            birth_date = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        except Exception:
            return None
    today = datetime.date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_patients_list(search_query=None, limit=50, offset=0):
    """
    Returns patient summaries along with their top conditions and twin pairing status.
    """
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            params = []
            where_clauses = []

            if search_query:
                where_clauses.append("(p.first_name LIKE %s OR p.last_name LIKE %s OR c.display_name LIKE %s)")
                q = f"%{search_query.strip()}%"
                params.extend([q, q, q])

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            query = f"""
                SELECT DISTINCT
                    p.id, p.patient_uuid, p.first_name, p.last_name, p.gender,
                    p.birth_date, p.city, p.state,
                    t.id AS twin_id, t.twin_name, t.twin_status, t.paired_cgm_user_id,
                    t.baseline_hba1c, t.risk_level
                FROM patients p
                LEFT JOIN twin_profiles t ON p.id = t.patient_id
                LEFT JOIN conditions c ON p.id = c.patient_id
                {where_sql}
                ORDER BY (t.paired_cgm_user_id IS NOT NULL) DESC, p.id ASC
                LIMIT %s OFFSET %s;
            """
            params.extend([limit, offset])
            cursor.execute(query, tuple(params))
            patients = cursor.fetchall()

            # For each patient, fetch top 3 conditions
            for p in patients:
                p['age'] = calculate_age(p['birth_date'])
                cursor.execute("""
                    SELECT display_name, code, status 
                    FROM conditions 
                    WHERE patient_id = %s 
                    ORDER BY id ASC 
                    LIMIT 3;
                """, (p['id'],))
                p['top_conditions'] = cursor.fetchall()

            return patients
    finally:
        conn.close()

def get_patient_profile(patient_id):
    """
    Returns comprehensive clinical details for a single patient:
    demographics, conditions list, medications list, and twin profile.
    """
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            # 1. Demographic profile
            cursor.execute("""
                SELECT p.*, t.id AS twin_id, t.twin_name, t.twin_status,
                       t.baseline_hba1c, t.target_glucose_min, t.target_glucose_max,
                       t.insulin_sensitivity, t.carb_ratio, t.paired_cgm_user_id,
                       t.paired_wearable_subject_id, t.risk_level, t.last_sync_time
                FROM patients p
                LEFT JOIN twin_profiles t ON p.id = t.patient_id
                WHERE p.id = %s;
            """, (patient_id,))
            patient = cursor.fetchone()
            if not patient:
                return None

            patient['age'] = calculate_age(patient['birth_date'])

            # 2. Medical Conditions (Problems)
            cursor.execute("""
                SELECT id, code, display_name, code_system, onset_date, resolved_date, status
                FROM conditions
                WHERE patient_id = %s
                ORDER BY onset_date DESC, id DESC;
            """, (patient_id,))
            patient['conditions'] = cursor.fetchall()

            # 3. Medications
            cursor.execute("""
                SELECT id, medication_name, rxnorm_code, start_date, stop_date, status
                FROM medications
                WHERE patient_id = %s
                ORDER BY start_date DESC, id DESC;
            """, (patient_id,))
            patient['medications'] = cursor.fetchall()

            return patient
    finally:
        conn.close()
