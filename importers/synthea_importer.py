import os
import glob
import xml.etree.ElementTree as ET
from datetime import datetime
from database import get_connection
from config import Config

def parse_hl7_date(date_str):
    """
    Parses HL7 date string formats like '19810525222000' or '19810525' into 'YYYY-MM-DD'.
    Returns None if empty or invalid.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()[:8]
    if len(cleaned) == 8 and cleaned.isdigit():
        try:
            dt = datetime.strptime(cleaned, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None

def parse_synthea_file(file_path):
    """
    Parses a single Synthea C-CDA XML file and extracts:
    - patient demographics
    - clinical conditions (Problems)
    - medications
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'s': 'urn:hl7-org:v3'}

    # 1. Patient UUID
    id_elem = root.find('.//s:recordTarget/s:patientRole/s:id', ns)
    patient_uuid = id_elem.attrib.get('extension') if id_elem is not None else None
    
    # Fallback to file name if XML id tag is missing
    if not patient_uuid:
        base = os.path.basename(file_path)
        parts = base.replace('.xml', '').split('_')
        patient_uuid = parts[-1] if len(parts) > 1 else base

    # 2. Patient Demographics
    p_elem = root.find('.//s:recordTarget/s:patientRole/s:patient', ns)
    if p_elem is None:
        raise ValueError(f"Patient element not found in {file_path}")

    first_name = p_elem.findtext('s:name/s:given', default='Unknown', namespaces=ns).strip()
    last_name = p_elem.findtext('s:name/s:family', default='Unknown', namespaces=ns).strip()
    
    gender_elem = p_elem.find('s:administrativeGenderCode', ns)
    gender = gender_elem.attrib.get('code', 'UN') if gender_elem is not None else 'UN'

    birth_elem = p_elem.find('s:birthTime', ns)
    birth_raw = birth_elem.attrib.get('value', '') if birth_elem is not None else ''
    birth_date = parse_hl7_date(birth_raw)

    race_elem = p_elem.find('s:raceCode', ns)
    race = race_elem.attrib.get('displayName', '') if race_elem is not None else ''

    eth_elem = p_elem.find('s:ethnicGroupCode', ns)
    ethnicity = eth_elem.attrib.get('displayName', '') if eth_elem is not None else ''

    addr_elem = root.find('.//s:recordTarget/s:patientRole/s:addr', ns)
    city = addr_elem.findtext('s:city', default='', namespaces=ns).strip() if addr_elem is not None else ''
    state = addr_elem.findtext('s:state', default='', namespaces=ns).strip() if addr_elem is not None else ''

    patient_data = {
        'patient_uuid': patient_uuid,
        'first_name': first_name,
        'last_name': last_name,
        'gender': gender,
        'birth_date': birth_date,
        'ethnicity': ethnicity,
        'race': race,
        'city': city,
        'state': state,
        'source_file': os.path.basename(file_path)
    }

    # 3. Clinical Conditions (Problems section code: 11450-4)
    conditions = []
    for sec in root.findall('.//{urn:hl7-org:v3}section'):
        code_elem = sec.find('{urn:hl7-org:v3}code')
        if code_elem is not None and code_elem.attrib.get('code') == '11450-4':
            for tr in sec.findall('.//{urn:hl7-org:v3}tr'):
                tds = tr.findall('{urn:hl7-org:v3}td')
                if len(tds) >= 4:
                    onset = tds[0].text.strip() if tds[0].text else None
                    resolved = tds[1].text.strip() if tds[1].text else None
                    name = tds[2].text.strip() if tds[2].text else None
                    code_raw = tds[3].text.strip() if tds[3].text else None
                    if name:
                        code_val = code_raw.split()[-1] if code_raw else 'SNOMED'
                        status = 'resolved' if resolved else 'active'
                        conditions.append({
                            'display_name': name[:250],
                            'code': code_val[:50],
                            'code_system': 'SNOMED-CT',
                            'onset_date': onset[:50] if onset else None,
                            'resolved_date': resolved[:50] if resolved else None,
                            'status': status
                        })

    # 4. Medications (Medications section code: 10160-0)
    medications = []
    for sec in root.findall('.//{urn:hl7-org:v3}section'):
        code_elem = sec.find('{urn:hl7-org:v3}code')
        if code_elem is not None and code_elem.attrib.get('code') == '10160-0':
            for tr in sec.findall('.//{urn:hl7-org:v3}tr'):
                tds = tr.findall('{urn:hl7-org:v3}td')
                if len(tds) >= 4:
                    start = tds[0].text.strip() if tds[0].text else None
                    stop = tds[1].text.strip() if tds[1].text else None
                    name = tds[2].text.strip() if tds[2].text else None
                    code_raw = tds[3].text.strip() if tds[3].text else None
                    if name:
                        rx_code = code_raw.split()[-1] if code_raw else ''
                        status = 'discontinued' if stop else 'active'
                        medications.append({
                            'medication_name': name[:250],
                            'rxnorm_code': rx_code[:50],
                            'start_date': start[:50] if start else None,
                            'stop_date': stop[:50] if stop else None,
                            'status': status
                        })

    return patient_data, conditions, medications

def import_synthea_data(directory=None, limit=None):
    """
    Imports all Synthea XML files into MySQL with idempotency (prevents duplicates).
    """
    directory = directory or Config.SYNTHEA_DIR
    xml_files = sorted(glob.glob(os.path.join(directory, "*.xml")))
    if limit:
        xml_files = xml_files[:limit]

    print(f"[*] Starting Synthea import: found {len(xml_files)} XML files in {directory}")

    conn = get_connection(use_database=True)
    stats = {
        'files_processed': 0,
        'patients_saved': 0,
        'conditions_saved': 0,
        'medications_saved': 0,
        'errors': 0
    }

    try:
        with conn.cursor() as cursor:
            for file_path in xml_files:
                try:
                    patient_data, conditions, medications = parse_synthea_file(file_path)

                    # 1. Upsert Patient
                    patient_sql = """
                        INSERT INTO patients (
                            patient_uuid, first_name, last_name, gender, birth_date,
                            ethnicity, race, city, state, source_file
                        ) VALUES (
                            %(patient_uuid)s, %(first_name)s, %(last_name)s, %(gender)s, %(birth_date)s,
                            %(ethnicity)s, %(race)s, %(city)s, %(state)s, %(source_file)s
                        )
                        ON DUPLICATE KEY UPDATE
                            first_name = VALUES(first_name),
                            last_name = VALUES(last_name),
                            gender = VALUES(gender),
                            birth_date = VALUES(birth_date),
                            city = VALUES(city),
                            state = VALUES(state);
                    """
                    cursor.execute(patient_sql, patient_data)
                    stats['patients_saved'] += 1

                    # Fetch internal auto-increment patient ID
                    cursor.execute("SELECT id FROM patients WHERE patient_uuid = %s;", (patient_data['patient_uuid'],))
                    patient_row = cursor.fetchone()
                    patient_id = patient_row['id']

                    # 2. Upsert Conditions
                    for cond in conditions:
                        cond_sql = """
                            INSERT INTO conditions (
                                patient_id, code, display_name, code_system, onset_date, resolved_date, status
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s
                            )
                            ON DUPLICATE KEY UPDATE
                                status = VALUES(status),
                                resolved_date = VALUES(resolved_date);
                        """
                        cursor.execute(cond_sql, (
                            patient_id, cond['code'], cond['display_name'], cond['code_system'],
                            cond['onset_date'], cond['resolved_date'], cond['status']
                        ))
                        stats['conditions_saved'] += 1

                    # 3. Upsert Medications
                    for med in medications:
                        med_sql = """
                            INSERT INTO medications (
                                patient_id, medication_name, rxnorm_code, start_date, stop_date, status
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s
                            )
                            ON DUPLICATE KEY UPDATE
                                status = VALUES(status),
                                stop_date = VALUES(stop_date);
                        """
                        cursor.execute(med_sql, (
                            patient_id, med['medication_name'], med['rxnorm_code'],
                            med['start_date'], med['stop_date'], med['status']
                        ))
                        stats['medications_saved'] += 1

                    stats['files_processed'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    print(f"[-] Error processing {os.path.basename(file_path)}: {e}")

            conn.commit()
            print(f"[+] Synthea import complete. Summary: {stats}")
            return stats
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    import_synthea_data()
