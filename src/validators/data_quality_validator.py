"""
Data Quality Validator
Implements great_expectations-style validation rules for all clinical data sources.
Produces validation reports and enforces quality gates.
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__, "logs/validator.log")


class ValidationResult:
    def __init__(self, check_name: str, passed: bool, details: dict = None):
        self.check_name = check_name
        self.passed = passed
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "check": self.check_name,
            "status": "PASS" if self.passed else "FAIL",
            "details": self.details,
            "timestamp": self.timestamp
        }


class DataQualityValidator:
    """
    Runs automated quality gates against all 8 clinical data sources.
    Implements checks equivalent to great_expectations suites.
    """

    def __init__(self, quality_threshold: float = 0.95, output_dir: str = "./outputs"):
        self.quality_threshold = quality_threshold
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, List[ValidationResult]] = {}
        logger.info(f"DataQualityValidator initialized | threshold={quality_threshold*100:.0f}%")

    # ─── Generic Checks ────────────────────────────────────────────────────

    def check_not_null(self, df: pd.DataFrame, column: str) -> ValidationResult:
        null_count = df[column].isna().sum()
        total = len(df)
        null_pct = null_count / max(total, 1)
        passed = null_pct < 0.01  # < 1% null allowed
        return ValidationResult(
            f"not_null::{column}",
            passed,
            {"null_count": int(null_count), "null_pct": f"{null_pct*100:.2f}%", "total": total}
        )

    def check_unique(self, df: pd.DataFrame, column: str) -> ValidationResult:
        dupes = df[column].duplicated().sum()
        passed = dupes == 0
        return ValidationResult(
            f"unique::{column}",
            passed,
            {"duplicate_count": int(dupes), "total": len(df)}
        )

    def check_in_set(self, df: pd.DataFrame, column: str, valid_set: set) -> ValidationResult:
        invalid = ~df[column].isin(valid_set)
        invalid_count = invalid.sum()
        invalid_pct = invalid_count / max(len(df), 1)
        passed = invalid_pct < 0.001
        return ValidationResult(
            f"in_set::{column}",
            passed,
            {"invalid_count": int(invalid_count), "invalid_pct": f"{invalid_pct*100:.3f}%",
             "sample_invalids": list(df.loc[invalid, column].head(3).astype(str))}
        )

    def check_range(self, df: pd.DataFrame, column: str, min_val=None, max_val=None) -> ValidationResult:
        series = df[column].dropna()
        violations = pd.Series([False] * len(series))
        if min_val is not None:
            violations |= (series < min_val)
        if max_val is not None:
            violations |= (series > max_val)
        viol_count = violations.sum()
        viol_pct = viol_count / max(len(series), 1)
        passed = viol_pct < 0.005
        return ValidationResult(
            f"range::{column}[{min_val},{max_val}]",
            passed,
            {"violation_count": int(viol_count), "violation_pct": f"{viol_pct*100:.3f}%"}
        )

    def check_date_range(self, df: pd.DataFrame, column: str,
                         min_date: str = "2000-01-01", max_date: str = None) -> ValidationResult:
        series = pd.to_datetime(df[column], errors="coerce", utc=False)
        # Strip timezone if present
        if hasattr(series.dtype, 'tz') and series.dtype.tz is not None:
            series = series.dt.tz_localize(None)
        null_dt = series.isna().sum()
        # Allow up to 90 days in the future (scheduled admissions/appointments are valid)
        future_dt = (series > pd.Timestamp.now() + pd.Timedelta(days=90)).sum() if max_date is None else 0
        old_dt = (series < pd.Timestamp(min_date)).sum()
        violations = int(null_dt + future_dt + old_dt)
        passed = violations / max(len(df), 1) < 0.01
        return ValidationResult(
            f"date_range::{column}",
            passed,
            {"null_dates": int(null_dt), "future_dates": int(future_dt), "old_dates": int(old_dt)}
        )

    def check_referential_integrity(self, df: pd.DataFrame, fk_col: str,
                                    ref_ids: set, allow_null: bool = True) -> ValidationResult:
        fk_vals = df[fk_col].dropna().astype(str) if allow_null else df[fk_col].astype(str)
        ref_ids_str = {str(x) for x in ref_ids}
        orphans = fk_vals[~fk_vals.isin(ref_ids_str)]
        orphan_count = len(orphans)
        orphan_pct = orphan_count / max(len(fk_vals), 1)
        passed = orphan_pct < 0.005
        return ValidationResult(
            f"referential_integrity::{fk_col}",
            passed,
            {"orphan_count": int(orphan_count), "orphan_pct": f"{orphan_pct*100:.3f}%"}
        )

    # ─── Source-Specific Validation Suites ────────────────────────────────

    def validate_patients(self, df: pd.DataFrame) -> Tuple[float, List[ValidationResult]]:
        results = [
            self.check_not_null(df, "patient_id"),
            self.check_not_null(df, "mrn"),
            self.check_unique(df, "patient_id"),
            self.check_unique(df, "mrn"),
            self.check_in_set(df, "gender", {"MALE", "FEMALE", "OTHER", "UNKNOWN"}),
            self.check_not_null(df, "zip_code"),
            self.check_not_null(df, "insurance_type"),
            self.check_date_range(df, "dob", min_date="1900-01-01"),
        ]
        if "age_years" in df.columns:
            results.append(self.check_range(df, "age_years", min_val=0, max_val=130))
        return self._compute_score(results), results

    def validate_encounters(self, df: pd.DataFrame, patient_ids: set) -> Tuple[float, List[ValidationResult]]:
        results = [
            self.check_not_null(df, "encounter_id"),
            self.check_not_null(df, "patient_id"),
            self.check_unique(df, "encounter_id"),
            self.check_referential_integrity(df, "patient_id", patient_ids, allow_null=False),
            self.check_in_set(df, "encounter_type", {"INPATIENT", "OUTPATIENT", "ED", "TELEHEALTH"}),
            self.check_date_range(df, "admit_datetime"),
            self.check_not_null(df, "primary_diagnosis_icd10"),
        ]
        if "los_days" in df.columns:
            results.append(self.check_range(df, "los_days", min_val=0, max_val=365))
        return self._compute_score(results), results

    def validate_labs(self, df: pd.DataFrame, patient_ids: set) -> Tuple[float, List[ValidationResult]]:
        results = [
            self.check_not_null(df, "lab_result_id"),
            self.check_not_null(df, "patient_id"),
            self.check_not_null(df, "loinc_code"),
            self.check_referential_integrity(df, "patient_id", patient_ids),
            self.check_in_set(df, "abnormal_flag", {"N", "H", "L", "HH", "LL", None, "None"}),
            self.check_date_range(df, "collected_datetime"),
            self.check_date_range(df, "resulted_datetime"),
        ]
        if "tat_hours" in df.columns:
            results.append(self.check_range(df, "tat_hours", min_val=0, max_val=168))
        return self._compute_score(results), results

    def validate_billing(self, df: pd.DataFrame) -> Tuple[float, List[ValidationResult]]:
        results = [
            self.check_not_null(df, "claim_id"),
            self.check_not_null(df, "patient_id"),
            self.check_not_null(df, "cpt_code"),
            self.check_range(df, "charge_amount", min_val=0, max_val=1000000),
            self.check_in_set(df, "claim_status", {"PAID", "PENDING", "DENIED", "SUBMITTED"}),
            self.check_not_null(df, "payer_name"),
        ]
        return self._compute_score(results), results

    def validate_icu_vitals(self, df: pd.DataFrame) -> Tuple[float, List[ValidationResult]]:
        results = [
            self.check_not_null(df, "vital_id"),
            self.check_not_null(df, "patient_id"),
            self.check_not_null(df, "timestamp"),
            self.check_range(df, "heart_rate", min_val=20, max_val=250),
            self.check_range(df, "systolic_bp", min_val=40, max_val=280),
            self.check_range(df, "spo2", min_val=50, max_val=100),
            self.check_range(df, "temperature_celsius", min_val=28, max_val=44),
        ]
        return self._compute_score(results), results

    # ─── Scoring & Reporting ───────────────────────────────────────────────

    def _compute_score(self, results: List[ValidationResult]) -> float:
        if not results:
            return 1.0
        return sum(1 for r in results if r.passed) / len(results)

    def run_full_suite(self, data: Dict[str, pd.DataFrame], patient_ids: set = None) -> Dict:
        """Run all validation suites and produce a summary report."""
        logger.info("=" * 60)
        logger.info("RUNNING FULL DATA QUALITY VALIDATION SUITE")
        logger.info("=" * 60)

        report = {
            "run_timestamp": datetime.utcnow().isoformat(),
            "threshold": self.quality_threshold,
            "sources": {},
            "overall_score": 0.0,
            "gate_passed": False,
        }

        pid_set = patient_ids or set()
        scores = []

        # Patients
        if "patients" in data and len(data["patients"]) > 0:
            score, results = self.validate_patients(data["patients"])
            report["sources"]["patients"] = self._source_report("patients", score, results, len(data["patients"]))
            scores.append(score)

        # Encounters
        if "encounters" in data and len(data["encounters"]) > 0:
            score, results = self.validate_encounters(data["encounters"], pid_set)
            report["sources"]["encounters"] = self._source_report("encounters", score, results, len(data["encounters"]))
            scores.append(score)

        # Labs
        if "labs" in data and len(data["labs"]) > 0:
            score, results = self.validate_labs(data["labs"], pid_set)
            report["sources"]["labs"] = self._source_report("labs", score, results, len(data["labs"]))
            scores.append(score)

        # Billing
        if "billing" in data and len(data["billing"]) > 0:
            score, results = self.validate_billing(data["billing"])
            report["sources"]["billing"] = self._source_report("billing", score, results, len(data["billing"]))
            scores.append(score)

        # ICU Vitals
        if "icu_vitals" in data and len(data["icu_vitals"]) > 0:
            score, results = self.validate_icu_vitals(data["icu_vitals"])
            report["sources"]["icu_vitals"] = self._source_report("icu_vitals", score, results, len(data["icu_vitals"]))
            scores.append(score)

        overall = sum(scores) / max(len(scores), 1)
        report["overall_score"] = round(overall, 4)
        report["overall_score_pct"] = f"{overall*100:.2f}%"
        report["gate_passed"] = overall >= self.quality_threshold

        # Log results
        logger.info(f"\n{'─'*60}")
        for src, info in report["sources"].items():
            status = "✅" if info["gate_passed"] else "❌"
            logger.info(f"  {status} {src:20s} | Score: {info['score_pct']} | Records: {info['record_count']:,}")
        logger.info(f"{'─'*60}")
        logger.info(f"  OVERALL QUALITY: {report['overall_score_pct']} | Gate: {'PASSED ✅' if report['gate_passed'] else 'FAILED ❌'}")
        logger.info(f"{'='*60}")

        # Save report
        report_path = self.output_dir / "data_quality_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"  Quality report saved: {report_path}")

        return report

    def _source_report(self, name: str, score: float, results: List[ValidationResult], record_count: int) -> dict:
        return {
            "source": name,
            "record_count": record_count,
            "score": round(score, 4),
            "score_pct": f"{score*100:.2f}%",
            "gate_passed": score >= self.quality_threshold,
            "checks": [r.to_dict() for r in results],
            "checks_passed": sum(1 for r in results if r.passed),
            "checks_total": len(results),
        }
