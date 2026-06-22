"""
Unit Tests for Clinical ETL Platform
Tests extractors, transformers, validators, and loaders.
Run: python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
import pandas as pd
import tempfile
from datetime import datetime
from src.extractors.ehr_extractor import EHRExtractor
from src.extractors.lab_extractor import LabExtractor
from src.extractors.other_extractors import (
    BillingExtractor, ICUExtractor, HRExtractor
)
from src.transformers.clinical_transformer import ClinicalTransformer
from src.validators.data_quality_validator import DataQualityValidator, ValidationResult
from src.loaders.snowflake_loader import SnowflakeLoader


class TestEHRExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = EHRExtractor({}, demo_mode=True)

    def test_extract_patients_returns_correct_count(self):
        records = self.extractor.extract_patients(num_records=100)
        self.assertEqual(len(records), 100)

    def test_patient_has_required_fields(self):
        records = self.extractor.extract_patients(num_records=10)
        for r in records:
            self.assertIn("patient_id", r)
            self.assertIn("mrn", r)
            self.assertIn("gender", r)
            self.assertIn("dob", r)
            self.assertIn("insurance_type", r)
            self.assertIsNotNone(r["patient_id"])

    def test_patient_gender_valid(self):
        records = self.extractor.extract_patients(num_records=50)
        for r in records:
            self.assertIn(r["gender"], ["M", "F"])

    def test_phi_is_masked(self):
        records = self.extractor.extract_patients(num_records=10)
        for r in records:
            self.assertTrue(r["mrn"].startswith("PHI_"),
                            f"MRN not masked: {r['mrn']}")

    def test_extract_encounters_uses_provided_patient_ids(self):
        patients = self.extractor.extract_patients(num_records=50)
        pids = [p["patient_id"] for p in patients]
        encounters = self.extractor.extract_encounters(pids, num_records=100)
        self.assertEqual(len(encounters), 100)
        enc_pids = {e["patient_id"] for e in encounters}
        self.assertTrue(enc_pids.issubset(set(pids)),
                        "Encounter patient_ids should be from provided list")

    def test_encounter_types_valid(self):
        patients = self.extractor.extract_patients(num_records=20)
        pids = [p["patient_id"] for p in patients]
        encounters = self.extractor.extract_encounters(pids, num_records=50)
        valid_types = {"INPATIENT", "OUTPATIENT", "ED", "TELEHEALTH"}
        for e in encounters:
            self.assertIn(e["encounter_type"], valid_types)

    def test_inpatient_has_discharge_datetime(self):
        patients = self.extractor.extract_patients(num_records=20)
        pids = [p["patient_id"] for p in patients]
        encounters = self.extractor.extract_encounters(pids, num_records=200)
        inpatient = [e for e in encounters if e["encounter_type"] == "INPATIENT"]
        for e in inpatient:
            self.assertIsNotNone(e["discharge_datetime"])
            self.assertIsNotNone(e["los_days"])
            self.assertGreater(e["los_days"], 0)


class TestLabExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = LabExtractor({}, demo_mode=True)
        ehr = EHRExtractor({}, demo_mode=True)
        patients = ehr.extract_patients(50)
        self.pids = [p["patient_id"] for p in patients]
        encounters = ehr.extract_encounters(self.pids, 100)
        self.eids = [e["encounter_id"] for e in encounters]

    def test_extract_returns_correct_count(self):
        records = self.extractor.extract(self.pids, self.eids, num_records=200)
        self.assertEqual(len(records), 200)

    def test_lab_has_loinc_code(self):
        records = self.extractor.extract(self.pids, self.eids, num_records=50)
        for r in records:
            self.assertIn("loinc_code", r)
            self.assertIsNotNone(r["loinc_code"])

    def test_abnormal_flags_valid(self):
        records = self.extractor.extract(self.pids, self.eids, num_records=100)
        valid_flags = {"N", "H", "L", "HH", "LL", None}
        for r in records:
            self.assertIn(r["abnormal_flag"], valid_flags)

    def test_abnormal_rate_reasonable(self):
        records = self.extractor.extract(self.pids, self.eids, num_records=1000)
        abnormal = sum(1 for r in records if r["abnormal_flag"] in ("H","L","HH","LL"))
        rate = abnormal / len(records)
        self.assertGreater(rate, 0.05, "Abnormal rate too low")
        self.assertLess(rate, 0.50, "Abnormal rate too high")


class TestClinicalTransformer(unittest.TestCase):

    def setUp(self):
        self.transformer = ClinicalTransformer(demo_mode=True)
        ehr = EHRExtractor({}, demo_mode=True)
        patients = ehr.extract_patients(200)
        self.pids = [p["patient_id"] for p in patients]
        self.patients_raw = patients
        encounters = ehr.extract_encounters(self.pids, 300)
        self.encounters_raw = encounters

    def test_transform_patients_returns_dataframe(self):
        df = self.transformer.transform_patients(self.patients_raw)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), len(self.patients_raw))

    def test_gender_normalized(self):
        df = self.transformer.transform_patients(self.patients_raw)
        valid = {"MALE", "FEMALE", "OTHER", "UNKNOWN"}
        self.assertTrue(df["gender"].isin(valid).all(),
                        f"Invalid genders: {df['gender'].unique()}")

    def test_age_group_assigned(self):
        df = self.transformer.transform_patients(self.patients_raw)
        self.assertIn("age_group", df.columns)
        self.assertFalse(df["age_group"].isna().all())

    def test_transform_encounters_computes_los(self):
        df = self.transformer.transform_encounters(self.encounters_raw)
        inpatient = df[df["encounter_type"] == "INPATIENT"]
        if len(inpatient) > 0:
            self.assertTrue((inpatient["los_days"] >= 0).all())

    def test_transform_encounters_adds_los_risk(self):
        df = self.transformer.transform_encounters(self.encounters_raw)
        self.assertIn("los_risk", df.columns)
        valid_risk = {"NORMAL", "EXTENDED", "CRITICAL"}
        self.assertTrue(df["los_risk"].isin(valid_risk).all())

    def test_deduplication_removes_dupes(self):
        # Create patients with duplicate MRNs
        dupe_patients = self.patients_raw[:50] + self.patients_raw[:10]
        df = self.transformer.transform_patients(dupe_patients)
        self.assertEqual(len(df), 50, "Deduplication should remove 10 dupes")


class TestDataQualityValidator(unittest.TestCase):

    def setUp(self):
        self.validator = DataQualityValidator(quality_threshold=0.95)
        ehr = EHRExtractor({}, demo_mode=True)
        transformer = ClinicalTransformer(demo_mode=True)
        patients = ehr.extract_patients(500)
        self.pids = [p["patient_id"] for p in patients]
        self.patients_df = transformer.transform_patients(patients)

    def test_check_not_null_passes(self):
        result = self.validator.check_not_null(self.patients_df, "patient_id")
        self.assertTrue(result.passed)

    def test_check_not_null_fails_on_nulls(self):
        df = self.patients_df.copy()
        df.loc[:50, "patient_id"] = None
        result = self.validator.check_not_null(df, "patient_id")
        self.assertFalse(result.passed)

    def test_check_unique_passes(self):
        result = self.validator.check_unique(self.patients_df, "patient_id")
        self.assertTrue(result.passed)

    def test_check_unique_fails_on_dupes(self):
        df = pd.concat([self.patients_df, self.patients_df.head(10)])
        result = self.validator.check_unique(df, "patient_id")
        self.assertFalse(result.passed)

    def test_check_in_set_passes(self):
        result = self.validator.check_in_set(
            self.patients_df, "gender", {"MALE", "FEMALE", "OTHER", "UNKNOWN"}
        )
        self.assertTrue(result.passed)

    def test_check_range_passes(self):
        result = self.validator.check_range(self.patients_df, "age_years", 0, 130)
        self.assertTrue(result.passed)

    def test_validate_patients_high_score(self):
        score, results = self.validator.validate_patients(self.patients_df)
        self.assertGreaterEqual(score, 0.95, f"Patient quality score too low: {score}")

    def test_validation_result_dict(self):
        r = ValidationResult("test_check", True, {"count": 5})
        d = r.to_dict()
        self.assertEqual(d["check"], "test_check")
        self.assertEqual(d["status"], "PASS")


class TestSnowflakeLoader(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_clinical.db")
        self.loader = SnowflakeLoader(None, demo_mode=True, db_path=self.db_path)

    def test_connect_creates_db(self):
        self.loader.connect()
        self.assertTrue(os.path.exists(self.db_path))

    def test_load_dataframe_success(self):
        self.loader.connect()
        df = pd.DataFrame({
            "patient_id": ["P001", "P002"],
            "mrn": ["MRN001", "MRN002"],
            "gender": ["MALE", "FEMALE"],
            "dob": ["1980-01-01", "1975-05-15"],
            "zip_code": ["63101", "63102"],
            "insurance_type": ["MEDICARE", "BCBS"],
            "primary_physician_id": ["PHYS_001", "PHYS_002"],
            "age_years": [44, 49],
            "age_group": ["35-49", "35-49"],
            "source_system": ["EHR", "EHR"],
            "transformed_at": [datetime.utcnow().isoformat()]*2,
            "data_layer": ["SILVER"]*2,
        })
        count = self.loader.load_dataframe(df, "raw_patients", if_exists="replace")
        self.assertEqual(count, 2)

    def test_get_table_counts(self):
        self.loader.connect()
        df = pd.DataFrame({"patient_id": ["P1"], "mrn": ["M1"], "gender": ["M"],
                            "dob": ["1980-01-01"], "zip_code": ["63101"],
                            "insurance_type": ["MEDICARE"], "primary_physician_id": ["P"],
                            "age_years": [44], "age_group": ["35-49"],
                            "source_system": ["EHR"], "transformed_at": ["2024-01-01"],
                            "data_layer": ["SILVER"]})
        self.loader.load_dataframe(df, "raw_patients", if_exists="replace")
        counts = self.loader.get_table_counts()
        self.assertIn("raw_patients", counts)
        self.assertGreaterEqual(counts["raw_patients"], 1)

    def tearDown(self):
        self.loader.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
