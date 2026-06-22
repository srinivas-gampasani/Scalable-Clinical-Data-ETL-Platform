"""
Data schemas for all 8 clinical source systems.
Pure dataclass-based (no pydantic) for zero-dependency compatibility.
"""
import uuid
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Optional


def gen_id() -> str:
    return str(uuid.uuid4())


@dataclass
class PatientRecord:
    mrn: str
    gender: str
    dob: str
    zip_code: str
    insurance_type: str
    primary_physician_id: str
    patient_id: str = field(default_factory=gen_id)
    age_years: Optional[int] = None
    age_group: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    source_system: str = "EHR"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class EncounterRecord:
    patient_id: str
    encounter_type: str
    admit_datetime: str
    primary_diagnosis_icd10: str
    attending_physician_id: str
    department: str
    facility_id: str
    encounter_id: str = field(default_factory=gen_id)
    discharge_datetime: Optional[str] = None
    los_days: Optional[float] = None
    drg_code: Optional[str] = None
    source_system: str = "EHR"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class LabResultRecord:
    patient_id: str
    loinc_code: str
    test_name: str
    collected_datetime: str
    resulted_datetime: str
    ordering_physician_id: str
    lab_id: str
    lab_result_id: str = field(default_factory=gen_id)
    encounter_id: Optional[str] = None
    result_value: Optional[float] = None
    result_text: Optional[str] = None
    result_unit: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    abnormal_flag: Optional[str] = None
    source_system: str = "LAB"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class BillingRecord:
    patient_id: str
    encounter_id: str
    cpt_code: str
    icd10_code: str
    charge_amount: float
    payer_name: str
    claim_status: str
    service_date: str
    billing_date: str
    provider_npi: str
    facility_id: str
    claim_id: str = field(default_factory=gen_id)
    allowed_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    source_system: str = "BILLING"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class AppointmentRecord:
    patient_id: str
    provider_id: str
    appointment_type: str
    scheduled_datetime: str
    status: str
    department: str
    facility_id: str
    appointment_id: str = field(default_factory=gen_id)
    actual_start_datetime: Optional[str] = None
    actual_end_datetime: Optional[str] = None
    wait_time_days: Optional[int] = None
    referral_source: Optional[str] = None
    source_system: str = "SCHEDULING"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class MedicationRecord:
    patient_id: str
    rxnorm_code: str
    drug_name: str
    dose: str
    route: str
    frequency: str
    quantity_dispensed: float
    days_supply: int
    prescriber_npi: str
    dispensing_pharmacy_id: str
    prescribed_date: str
    status: str
    medication_id: str = field(default_factory=gen_id)
    encounter_id: Optional[str] = None
    dispensed_date: Optional[str] = None
    source_system: str = "PHARMACY"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class RadiologyRecord:
    patient_id: str
    accession_number: str
    modality: str
    body_part: str
    cpt_code: str
    study_datetime: str
    radiologist_id: str
    ordering_physician_id: str
    study_id: str = field(default_factory=gen_id)
    encounter_id: Optional[str] = None
    read_datetime: Optional[str] = None
    impression: Optional[str] = None
    finding_category: Optional[str] = None
    tat_hours: Optional[float] = None
    source_system: str = "RADIOLOGY"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class ICUVitalsRecord:
    patient_id: str
    encounter_id: str
    bed_id: str
    icu_unit: str
    timestamp: str
    vital_id: str = field(default_factory=gen_id)
    heart_rate: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    mean_arterial_pressure: Optional[float] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[float] = None
    temperature_celsius: Optional[float] = None
    etco2: Optional[float] = None
    alert_triggered: bool = False
    alert_type: Optional[str] = None
    source_system: str = "ICU_MONITOR"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()


@dataclass
class StaffRecord:
    employee_id: str
    role: str
    department: str
    facility_id: str
    hire_date: str
    employment_status: str
    staff_id: str = field(default_factory=gen_id)
    npi: Optional[str] = None
    license_type: Optional[str] = None
    license_expiry: Optional[str] = None
    shift_type: Optional[str] = None
    source_system: str = "HR"
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def dict(self):
        return self.__dict__.copy()
