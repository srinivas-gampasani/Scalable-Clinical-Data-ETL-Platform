"""Extractors for Billing, Scheduling, Pharmacy, Radiology, ICU, HR"""
import random, uuid
from datetime import datetime, timedelta, date
from typing import List, Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.models.schemas import (BillingRecord, AppointmentRecord, MedicationRecord,
    RadiologyRecord, ICUVitalsRecord, StaffRecord)
from src.utils.logger import get_logger

logger = get_logger(__name__, "logs/extractors.log")
random.seed(200)

CPT = ["99213","99214","99215","99232","99233","93000","71046","80053","36415","85025"]
PAYERS = ["MEDICARE","MEDICAID","BCBS","AETNA","UNITED","CIGNA","HUMANA"]
CLAIM_STATUS = ["PAID","PENDING","DENIED","SUBMITTED"]
APPT_TYPES = ["NEW_PATIENT","FOLLOW_UP","PROCEDURE","TELEHEALTH","ANNUAL_WELLNESS"]
APPT_STATUS = ["COMPLETED","CANCELLED","NO_SHOW","SCHEDULED"]
DRUGS = [
    ("1049502","Metformin 500mg","PO","BID"),("617312","Lisinopril 10mg","PO","QD"),
    ("310798","Atorvastatin 40mg","PO","QHS"),("308964","Omeprazole 20mg","PO","QD"),
    ("1049221","Amlodipine 5mg","PO","QD"),("197361","Albuterol 90mcg","INH","PRN"),
    ("1049630","Metoprolol 50mg","PO","BID"),("860975","Insulin Glargine 100U/mL","SQ","QHS"),
    ("310429","Furosemide 40mg","PO","QD"),("197803","Warfarin 5mg","PO","QD"),
]
MODALITIES = ["CT","MRI","XR","US","PET","NM","DEXA"]
BODY_PARTS = ["CHEST","ABDOMEN","HEAD","PELVIS","SPINE","KNEE","HIP","EXTREMITY"]
FINDINGS = ["NORMAL","ABNORMAL","CRITICAL","INDETERMINATE"]
ICU_UNITS = ["MICU","SICU","CVICU","NICU","BURN_ICU"]
ROLES = ["PHYSICIAN","RN","LPN","CNA","RT","PT","OT","PHARMACIST","ADMIN","TECH"]
DEPTS = ["CARDIOLOGY","EMERGENCY","ICU","ONCOLOGY","ORTHOPEDICS","NEUROLOGY",
         "PHARMACY","RADIOLOGY","PULMONOLOGY","INTERNAL_MEDICINE"]
FACILITIES = ["MAIN_CAMPUS","NORTH_WING","SOUTH_CLINIC"]

def _dt(base, days_range=30): return base + timedelta(days=random.uniform(0,days_range), hours=random.uniform(0,23))
def _d(base_date, days_range=30): return (datetime.combine(base_date, datetime.min.time()) + timedelta(days=random.randint(0,days_range))).strftime("%Y-%m-%d")

class BillingExtractor:
    def __init__(self, config, demo_mode=True): pass
    def extract(self, patient_ids, encounter_ids, n=8000):
        logger.info(f"Extracting {n} billing records...")
        base = date.today() - timedelta(days=30)
        records = []
        for _ in range(n):
            charge = round(random.uniform(150,15000),2)
            status = random.choice(CLAIM_STATUS)
            paid = round(charge*random.uniform(0.6,0.95),2) if status=="PAID" else None
            svc = _d(base)
            bill = (datetime.strptime(svc,"%Y-%m-%d")+timedelta(days=random.randint(1,5))).strftime("%Y-%m-%d")
            r = BillingRecord(
                patient_id=random.choice(patient_ids), encounter_id=random.choice(encounter_ids),
                cpt_code=random.choice(CPT), icd10_code=random.choice(["I10","E11.9","J18.9"]),
                charge_amount=charge, allowed_amount=round(charge*random.uniform(0.5,0.9),2),
                paid_amount=paid, payer_name=random.choice(PAYERS), claim_status=status,
                service_date=svc, billing_date=bill,
                provider_npi=f"NPI{random.randint(1000000000,1999999999)}",
                facility_id=random.choice(FACILITIES),
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} billing records"); return records

class SchedulingExtractor:
    def __init__(self, config, demo_mode=True): pass
    def extract(self, patient_ids, provider_ids, n=12000):
        logger.info(f"Extracting {n} scheduling records...")
        base = datetime.utcnow() - timedelta(days=30)
        records = []
        for _ in range(n):
            sched = _dt(base, 60)
            status = random.choice(APPT_STATUS)
            start = (sched + timedelta(minutes=random.randint(-15,45))).isoformat() if status=="COMPLETED" else None
            end = (datetime.fromisoformat(start)+timedelta(minutes=random.randint(15,60))).isoformat() if start else None
            r = AppointmentRecord(
                patient_id=random.choice(patient_ids), provider_id=random.choice(provider_ids),
                appointment_type=random.choice(APPT_TYPES), scheduled_datetime=sched.isoformat(),
                actual_start_datetime=start, actual_end_datetime=end,
                status=status, department=random.choice(DEPTS),
                facility_id=random.choice(FACILITIES), wait_time_days=random.randint(0,30),
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} scheduling records"); return records

class PharmacyExtractor:
    def __init__(self, config, demo_mode=True): pass
    def extract(self, patient_ids, encounter_ids, n=20000):
        logger.info(f"Extracting {n} pharmacy records...")
        base = date.today() - timedelta(days=30)
        records = []
        for _ in range(n):
            rxnorm, drug, route, freq = random.choice(DRUGS)
            days = random.choice([7,14,30,60,90])
            rx = _d(base)
            disp = (datetime.strptime(rx,"%Y-%m-%d")+timedelta(days=random.randint(0,2))).strftime("%Y-%m-%d") if random.random()>0.05 else None
            r = MedicationRecord(
                patient_id=random.choice(patient_ids),
                encounter_id=random.choice(encounter_ids) if random.random()>0.4 else None,
                rxnorm_code=rxnorm, drug_name=drug,
                dose=drug.split()[-1] if len(drug.split())>1 else "N/A",
                route=route, frequency=freq,
                quantity_dispensed=round(random.uniform(7,270),1), days_supply=days,
                prescriber_npi=f"NPI{random.randint(1000000000,1999999999)}",
                dispensing_pharmacy_id=f"RX_{random.randint(100,999)}",
                prescribed_date=rx, dispensed_date=disp,
                status=random.choice(["ACTIVE","DISCONTINUED","COMPLETED"]),
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} pharmacy records"); return records

class RadiologyExtractor:
    def __init__(self, config, demo_mode=True): pass
    def extract(self, patient_ids, encounter_ids, n=3000):
        logger.info(f"Extracting {n} radiology records...")
        base = datetime.utcnow() - timedelta(days=30)
        records = []
        for _ in range(n):
            study = _dt(base)
            tat = random.uniform(0.5,48)
            read = (study + timedelta(hours=tat)).isoformat()
            r = RadiologyRecord(
                patient_id=random.choice(patient_ids),
                encounter_id=random.choice(encounter_ids) if random.random()>0.4 else None,
                accession_number=f"ACC{random.randint(100000,999999)}",
                modality=random.choice(MODALITIES), body_part=random.choice(BODY_PARTS),
                cpt_code=random.choice(["71046","74178","70553","76805"]),
                study_datetime=study.isoformat(), read_datetime=read,
                radiologist_id=f"RAD_{random.randint(100,999)}",
                ordering_physician_id=f"PHYS_{random.randint(1000,9999)}",
                finding_category=random.choice(FINDINGS), tat_hours=round(tat,2),
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} radiology records"); return records

class ICUExtractor:
    def __init__(self, config, demo_mode=True): pass
    def extract(self, patient_ids, encounter_ids, n=50000):
        logger.info(f"Extracting {n} ICU vitals records...")
        base = datetime.utcnow() - timedelta(hours=24)
        icu_pts = random.sample(patient_ids, min(50, len(patient_ids)))
        records = []
        for i in range(n):
            pid = random.choice(icu_pts)
            ts = base + timedelta(seconds=i*1.7)
            hr = round(random.gauss(80,15),1)
            sbp = round(random.gauss(120,20),1)
            dbp = round(random.gauss(75,12),1)
            spo2 = round(random.gauss(97,2),1)
            rr = round(random.gauss(16,4),1)
            temp = round(random.gauss(37.0,0.5),1)
            alert, atype = False, None
            if hr<50 or hr>130: alert, atype = True, "TACHYCARDIA" if hr>130 else "BRADYCARDIA"
            elif spo2<90: alert, atype = True, "HYPOXIA"
            elif sbp<80 or sbp>180: alert, atype = True, "BP_CRITICAL"
            r = ICUVitalsRecord(
                patient_id=pid, encounter_id=random.choice(encounter_ids),
                bed_id=f"BED_{random.randint(1,30):02d}", icu_unit=random.choice(ICU_UNITS),
                timestamp=ts.isoformat(),
                heart_rate=max(30,min(200,hr)), systolic_bp=max(60,min(220,sbp)),
                diastolic_bp=max(40,min(140,dbp)),
                mean_arterial_pressure=round((sbp+2*dbp)/3,1),
                spo2=max(70,min(100,spo2)), respiratory_rate=max(6,min(40,rr)),
                temperature_celsius=max(35,min(41,temp)),
                alert_triggered=alert, alert_type=atype,
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} ICU vitals records"); return records

class HRExtractor:
    def __init__(self, config, demo_mode=True): pass
    def extract(self, n=500):
        logger.info(f"Extracting {n} HR records...")
        base = date.today() - timedelta(days=365*5)
        records = []
        for i in range(n):
            role = random.choice(ROLES)
            has_npi = role in ["PHYSICIAN","RN","LPN","PHARMACIST","RT","PT","OT"]
            hire = (datetime.combine(base,datetime.min.time())+timedelta(days=random.randint(0,365*5))).strftime("%Y-%m-%d")
            lic_exp = (date.today()+timedelta(days=random.randint(30,730))).strftime("%Y-%m-%d") if has_npi else None
            r = StaffRecord(
                employee_id=f"EMP{i+1:05d}", role=role, department=random.choice(DEPTS),
                facility_id=random.choice(FACILITIES),
                npi=f"NPI{random.randint(1000000000,1999999999)}" if has_npi else None,
                license_type=f"{role}_LICENSE" if has_npi else None, license_expiry=lic_exp,
                hire_date=hire,
                employment_status=random.choice(["ACTIVE","ACTIVE","ACTIVE","INACTIVE","ON_LEAVE"]),
                shift_type=random.choice(["DAY","NIGHT","EVENING","PRN"]),
            )
            records.append(r.dict())
        logger.info(f"  ✓ {len(records)} HR records"); return records
