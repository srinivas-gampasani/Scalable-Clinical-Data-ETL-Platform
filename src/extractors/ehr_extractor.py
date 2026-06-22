"""
EHR System Extractor — generates realistic synthetic clinical data.
"""
import random
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import List, Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.schemas import PatientRecord, EncounterRecord
from src.utils.logger import get_logger

logger = get_logger(__name__, "logs/ehr_extractor.log")
random.seed(42)

ICD10_CODES = ["I10","E11.9","J18.9","N39.0","I21.9","J44.1","F32.1","M54.5","K92.1","Z87.891"]
ENCOUNTER_TYPES = ["INPATIENT", "OUTPATIENT", "ED", "TELEHEALTH"]
DEPARTMENTS = ["CARDIOLOGY","INTERNAL_MEDICINE","EMERGENCY","ORTHOPEDICS","NEUROLOGY","ONCOLOGY","PULMONOLOGY"]
FACILITIES = ["MAIN_CAMPUS","NORTH_WING","SOUTH_CLINIC","WEST_HOSPITAL"]
INSURANCE = ["MEDICARE","MEDICAID","BCBS","AETNA","UNITED","CIGNA","SELF_PAY"]
RACES = ["WHITE","BLACK","ASIAN","HISPANIC","OTHER",None]
GENDERS = ["M","F"]

def _rand_date(start_year=1930, end_year=2006):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end-start).days))).strftime("%Y-%m-%d")

def _mask(val): return "PHI_" + hashlib.sha256(val.encode()).hexdigest()[:12]

class EHRExtractor:
    def __init__(self, config, demo_mode=True):
        self.demo_mode = demo_mode
        logger.info("EHRExtractor initialized")

    def extract_patients(self, num_records=5000):
        logger.info(f"Extracting {num_records} patient records...")
        records = []
        for i in range(num_records):
            dob = _rand_date()
            age = datetime.utcnow().year - int(dob[:4])
            if age < 18: ag = "0-17"
            elif age < 35: ag = "18-34"
            elif age < 50: ag = "35-49"
            elif age < 65: ag = "50-64"
            elif age < 80: ag = "65-79"
            else: ag = "80+"
            r = PatientRecord(
                mrn=_mask(f"MRN{i:07d}"),
                gender=random.choice(GENDERS),
                dob=dob,
                zip_code=f"{random.randint(10000,99999)}",
                insurance_type=random.choice(INSURANCE),
                primary_physician_id=f"PHYS_{random.randint(1000,9999)}",
                age_years=age,
                age_group=ag,
                race=random.choice(RACES),
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} patient records")
        return records

    def extract_encounters(self, patient_ids, num_records=8000):
        logger.info(f"Extracting {num_records} encounters...")
        records = []
        base = datetime.utcnow() - timedelta(days=30)
        for _ in range(num_records):
            admit = base + timedelta(days=random.uniform(0,30), hours=random.uniform(0,23))
            enc_type = random.choice(ENCOUNTER_TYPES)
            if enc_type == "INPATIENT":
                disc = admit + timedelta(days=random.uniform(1,14))
                los = round((disc-admit).total_seconds()/86400, 2)
            else:
                disc = admit + timedelta(hours=random.uniform(0.5,4))
                los = None
            r = EncounterRecord(
                patient_id=random.choice(patient_ids),
                encounter_type=enc_type,
                admit_datetime=admit.isoformat(),
                discharge_datetime=disc.isoformat(),
                primary_diagnosis_icd10=random.choice(ICD10_CODES),
                attending_physician_id=f"PHYS_{random.randint(1000,9999)}",
                department=random.choice(DEPARTMENTS),
                facility_id=random.choice(FACILITIES),
                los_days=los,
                drg_code=f"DRG_{random.randint(100,999)}" if enc_type=="INPATIENT" else None,
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} encounter records")
        return records
