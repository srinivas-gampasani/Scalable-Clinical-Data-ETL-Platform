"""Lab System Extractor"""
import random
from datetime import datetime, timedelta
from typing import List, Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.schemas import LabResultRecord
from src.utils.logger import get_logger

logger = get_logger(__name__, "logs/lab_extractor.log")
random.seed(100)

LAB_PANELS = [
    ("2160-0","Creatinine",0.5,1.2,"mg/dL"),
    ("2823-3","Potassium",3.5,5.0,"mEq/L"),
    ("2951-2","Sodium",136,145,"mEq/L"),
    ("718-7","Hemoglobin",12.0,17.5,"g/dL"),
    ("4544-3","Hematocrit",36.0,52.0,"%"),
    ("6690-2","WBC",4.5,11.0,"K/uL"),
    ("777-3","Platelets",150,400,"K/uL"),
    ("2345-7","Glucose",70,100,"mg/dL"),
    ("1742-6","ALT",7,56,"U/L"),
    ("1920-8","AST",10,40,"U/L"),
    ("4548-4","HbA1c",None,5.7,"%"),
    ("2093-3","Total Cholesterol",None,200,"mg/dL"),
    ("33914-3","eGFR",60,None,"mL/min/1.73m2"),
]

def _gauss_clamp(mu, sigma, lo=None, hi=None):
    v = random.gauss(mu, sigma)
    if lo: v = max(v, lo)
    if hi: v = min(v, hi)
    return round(v, 2)

def _flag(v, lo, hi):
    if v is None: return "N"
    if lo and v < lo: return "LL" if v < lo*0.7 else "L"
    if hi and v > hi: return "HH" if v > hi*1.3 else "H"
    return "N"

class LabExtractor:
    def __init__(self, config, demo_mode=True):
        self.demo_mode = demo_mode
        logger.info("LabExtractor initialized")

    def extract(self, patient_ids, encounter_ids, num_records=15000):
        logger.info(f"Extracting {num_records} lab results...")
        records = []
        base = datetime.utcnow() - timedelta(days=30)
        for _ in range(num_records):
            loinc, name, lo, hi, unit = random.choice(LAB_PANELS)
            coll = base + timedelta(days=random.uniform(0,30), hours=random.uniform(0,23))
            res = coll + timedelta(hours=random.uniform(1,6))
            if lo and hi: v = _gauss_clamp((lo+hi)/2, (hi-lo)*0.3, lo*0.1, hi*5)
            elif hi: v = _gauss_clamp(hi*0.75, hi*0.15, 0, hi*5)
            else: v = _gauss_clamp(lo*1.2, lo*0.15, 0)
            if random.random() < 0.15 and hi:
                v = round(v * random.uniform(1.2, 1.8), 2)
            r = LabResultRecord(
                patient_id=random.choice(patient_ids),
                encounter_id=random.choice(encounter_ids) if random.random()>0.3 else None,
                loinc_code=loinc, test_name=name,
                result_value=v, result_unit=unit,
                reference_range_low=lo, reference_range_high=hi,
                abnormal_flag=_flag(v, lo, hi),
                collected_datetime=coll.isoformat(),
                resulted_datetime=res.isoformat(),
                ordering_physician_id=f"PHYS_{random.randint(1000,9999)}",
                lab_id=f"LAB_{random.choice(['MAIN','SEND_OUT','STAT'])}",
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} lab records")
        return records
