"""
Snowflake Data Warehouse Loader
Loads transformed data into Snowflake schemas: RAW → STAGING → MARTS.
In demo mode, uses SQLite as a local substitute.
"""
import sqlite3
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__, "logs/loader.log")


class SnowflakeLoader:
    """
    Loads data to Snowflake (production) or SQLite (demo).
    Uses COPY INTO commands for bulk loading in production.
    Schema: RAW → STAGING → INTERMEDIATE → MARTS (Gold layer)
    """

    SCHEMAS = ["RAW", "STAGING", "INTERMEDIATE", "MARTS"]

    def __init__(self, config, demo_mode: bool = True, db_path: str = "./outputs/clinical_dw.db"):
        self.config = config
        self.demo_mode = demo_mode
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.load_stats: Dict = {}
        logger.info(f"SnowflakeLoader initialized | mode={'DEMO/SQLite' if demo_mode else 'SNOWFLAKE'}")

    def connect(self):
        if self.demo_mode:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._create_schemas()
            logger.info(f"  Connected to demo SQLite: {self.db_path}")
        else:
            import snowflake.connector
            self._conn = snowflake.connector.connect(
                account=self.config.account,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                warehouse=self.config.warehouse,
                schema=self.config.schema,
                role=self.config.role,
            )
            logger.info("  Connected to Snowflake")

    def _create_schemas(self):
        """Create schema tables for demo SQLite."""
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS raw_patients (
                patient_id TEXT PRIMARY KEY, mrn TEXT, gender TEXT, dob TEXT,
                age_years INTEGER, age_group TEXT, zip_code TEXT, insurance_type TEXT,
                primary_physician_id TEXT, source_system TEXT, extracted_at TEXT,
                transformed_at TEXT, data_layer TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_encounters (
                encounter_id TEXT PRIMARY KEY, patient_id TEXT, encounter_type TEXT,
                admit_datetime TEXT, discharge_datetime TEXT,
                primary_diagnosis_icd10 TEXT, attending_physician_id TEXT,
                department TEXT, facility_id TEXT, los_days REAL,
                los_risk TEXT, drg_code TEXT, year_month TEXT,
                encounter_hours REAL, source_system TEXT, data_layer TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_labs (
                lab_result_id TEXT PRIMARY KEY, patient_id TEXT, encounter_id TEXT,
                loinc_code TEXT, test_name TEXT, result_value REAL,
                result_unit TEXT, abnormal_flag TEXT, result_category TEXT,
                is_critical INTEGER, tat_hours REAL,
                collected_datetime TEXT, resulted_datetime TEXT,
                ordering_physician_id TEXT, lab_id TEXT, source_system TEXT, data_layer TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_billing (
                claim_id TEXT PRIMARY KEY, patient_id TEXT, encounter_id TEXT,
                cpt_code TEXT, icd10_code TEXT, charge_amount REAL,
                allowed_amount REAL, paid_amount REAL, payer_name TEXT,
                claim_status TEXT, service_date TEXT, billing_date TEXT,
                provider_npi TEXT, facility_id TEXT, source_system TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_appointments (
                appointment_id TEXT PRIMARY KEY, patient_id TEXT, provider_id TEXT,
                appointment_type TEXT, status TEXT, department TEXT,
                scheduled_datetime TEXT, actual_start_datetime TEXT,
                actual_end_datetime TEXT, facility_id TEXT, wait_time_days INTEGER,
                source_system TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_medications (
                medication_id TEXT PRIMARY KEY, patient_id TEXT, encounter_id TEXT,
                rxnorm_code TEXT, drug_name TEXT, dose TEXT, route TEXT,
                frequency TEXT, quantity_dispensed REAL, days_supply INTEGER,
                prescriber_npi TEXT, dispensing_pharmacy_id TEXT,
                prescribed_date TEXT, dispensed_date TEXT, status TEXT, source_system TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_radiology (
                study_id TEXT PRIMARY KEY, patient_id TEXT, encounter_id TEXT,
                accession_number TEXT, modality TEXT, body_part TEXT, cpt_code TEXT,
                study_datetime TEXT, read_datetime TEXT, radiologist_id TEXT,
                ordering_physician_id TEXT, finding_category TEXT, tat_hours REAL,
                source_system TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_icu_vitals (
                vital_id TEXT PRIMARY KEY, patient_id TEXT, encounter_id TEXT,
                bed_id TEXT, icu_unit TEXT, timestamp TEXT,
                heart_rate REAL, systolic_bp REAL, diastolic_bp REAL,
                mean_arterial_pressure REAL, spo2 REAL, respiratory_rate REAL,
                temperature_celsius REAL, map_calculated REAL, hr_rolling_avg REAL,
                vitals_status TEXT, alert_triggered INTEGER, alert_type TEXT,
                source_system TEXT, data_layer TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_staff (
                staff_id TEXT PRIMARY KEY, employee_id TEXT, role TEXT,
                department TEXT, facility_id TEXT, npi TEXT,
                hire_date TEXT, employment_status TEXT, shift_type TEXT, source_system TEXT
            );
            CREATE TABLE IF NOT EXISTS mart_patient_encounters (
                encounter_id TEXT PRIMARY KEY, patient_id TEXT, encounter_type TEXT,
                admit_datetime TEXT, discharge_datetime TEXT, los_days REAL,
                los_risk TEXT, department TEXT, facility_id TEXT,
                gender TEXT, age_years INTEGER, age_group TEXT,
                insurance_type TEXT, zip_code TEXT,
                lab_count REAL, critical_lab_count REAL, total_charges REAL,
                data_layer TEXT, mart_created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY, started_at TEXT, completed_at TEXT,
                status TEXT, total_records INTEGER, quality_score REAL,
                duration_minutes REAL, metrics_json TEXT
            );
        """)
        self._conn.commit()

    def load_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "append") -> int:
        """Load a DataFrame to target table."""
        if df is None or len(df) == 0:
            logger.warning(f"  Skipping empty DataFrame for table {table}")
            return 0

        # Serialize datetime columns
        for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
            df[col] = df[col].astype(str)

        # Convert boolean to int for SQLite
        for col in df.select_dtypes(include=["bool"]).columns:
            df[col] = df[col].astype(int)

        try:
            df.to_sql(table, self._conn, if_exists=if_exists, index=False, chunksize=5000)
            count = len(df)
            self.load_stats[table] = {"rows_loaded": count, "loaded_at": datetime.utcnow().isoformat()}
            logger.info(f"  ✓ Loaded {count:,} rows → {table}")
            return count
        except Exception as e:
            logger.error(f"  ✗ Failed to load {table}: {e}")
            raise

    def log_pipeline_run(self, run_id: str, started_at: datetime, status: str,
                         total_records: int, quality_score: float, metrics: dict):
        duration = (datetime.utcnow() - started_at).total_seconds() / 60
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pipeline_runs
            (run_id, started_at, completed_at, status, total_records, quality_score, duration_minutes, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, started_at.isoformat(), datetime.utcnow().isoformat(),
            status, total_records, quality_score, round(duration, 2), json.dumps(metrics)
        ))
        self._conn.commit()
        logger.info(f"  Pipeline run logged | Duration: {duration:.1f} min | Records: {total_records:,}")

    def get_table_counts(self) -> Dict[str, int]:
        """Return row counts for all tables."""
        counts = {}
        cursor = self._conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (table_name,) in cursor.fetchall():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            counts[table_name] = cursor.fetchone()[0]
        return counts

    def close(self):
        if self._conn:
            self._conn.close()
            logger.info("  Database connection closed")
