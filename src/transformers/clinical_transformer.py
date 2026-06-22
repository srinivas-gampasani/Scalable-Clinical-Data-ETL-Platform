"""
Clinical Data Transformer
Performs cleansing, normalization, deduplication, and FHIR mapping
using pandas (demo) or PySpark (production).
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__, "logs/transformer.log")


class ClinicalTransformer:
    """
    Transforms raw clinical data into canonical form for Snowflake loading.

    In production, this uses PySpark with Delta Lake for distributed
    processing of 100K+ records per run. In demo mode, uses pandas.
    """

    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.transformation_stats = {}
        logger.info(f"ClinicalTransformer initialized | mode={'DEMO' if demo_mode else 'SPARK'}")

    # ─── Patient Transformations ───────────────────────────────────────────

    def transform_patients(self, raw_records: List[Dict]) -> pd.DataFrame:
        logger.info(f"Transforming {len(raw_records)} patient records...")
        df = pd.DataFrame(raw_records)

        # Standardize gender
        df["gender"] = df["gender"].str.upper().map(
            {"M": "MALE", "F": "FEMALE", "O": "OTHER", "U": "UNKNOWN"}
        ).fillna("UNKNOWN")

        # Age calculation
        df["dob"] = pd.to_datetime(df["dob"])
        df["age_years"] = ((datetime.utcnow() - df["dob"]).dt.days / 365.25).astype(int)

        # Age buckets for analytics
        df["age_group"] = pd.cut(df["age_years"],
            bins=[0, 17, 34, 49, 64, 79, 200],
            labels=["0-17", "18-34", "35-49", "50-64", "65-79", "80+"]
        ).astype(str)

        # Deduplicate by MRN
        before = len(df)
        df = df.drop_duplicates(subset=["mrn"], keep="last")
        dupes = before - len(df)
        if dupes > 0:
            logger.info(f"  Removed {dupes} duplicate patient records")

        # Add metadata
        df["transformed_at"] = datetime.utcnow()
        df["data_layer"] = "SILVER"

        self.transformation_stats["patients"] = {
            "input": len(raw_records), "output": len(df), "dupes_removed": dupes
        }
        logger.info(f"  ✓ Transformed {len(df)} patient records")
        return df

    # ─── Encounter Transformations ─────────────────────────────────────────

    def transform_encounters(self, raw_records: List[Dict]) -> pd.DataFrame:
        logger.info(f"Transforming {len(raw_records)} encounter records...")
        df = pd.DataFrame(raw_records)

        df["admit_datetime"] = pd.to_datetime(df["admit_datetime"])
        df["discharge_datetime"] = pd.to_datetime(df["discharge_datetime"])

        # Recompute LOS for accuracy
        mask = df["discharge_datetime"].notna()
        df.loc[mask, "los_days"] = (
            (df.loc[mask, "discharge_datetime"] - df.loc[mask, "admit_datetime"])
            .dt.total_seconds() / 86400
        ).round(2)

        # LOS risk flag
        df["los_risk"] = "NORMAL"
        df.loc[df["los_days"] > 7, "los_risk"] = "EXTENDED"
        df.loc[df["los_days"] > 14, "los_risk"] = "CRITICAL"

        # Readmission window flag (simplified)
        df["year_month"] = df["admit_datetime"].dt.to_period("M").astype(str)

        # Encounter duration in hours
        df["encounter_hours"] = (
            (df["discharge_datetime"] - df["admit_datetime"]).dt.total_seconds() / 3600
        ).round(2)

        df["transformed_at"] = datetime.utcnow()
        df["data_layer"] = "SILVER"

        self.transformation_stats["encounters"] = {
            "input": len(raw_records), "output": len(df)
        }
        logger.info(f"  ✓ Transformed {len(df)} encounter records")
        return df

    # ─── Lab Transformations ───────────────────────────────────────────────

    def transform_labs(self, raw_records: List[Dict]) -> pd.DataFrame:
        logger.info(f"Transforming {len(raw_records)} lab records...")
        df = pd.DataFrame(raw_records)

        df["collected_datetime"] = pd.to_datetime(df["collected_datetime"])
        df["resulted_datetime"] = pd.to_datetime(df["resulted_datetime"])

        # Turnaround time
        df["tat_hours"] = (
            (df["resulted_datetime"] - df["collected_datetime"])
            .dt.total_seconds() / 3600
        ).round(2)

        # Critical value flag
        df["is_critical"] = df["abnormal_flag"].isin(["HH", "LL"])

        # Result classification
        df["result_category"] = "NORMAL"
        df.loc[df["abnormal_flag"].isin(["H", "L"]), "result_category"] = "ABNORMAL"
        df.loc[df["abnormal_flag"].isin(["HH", "LL"]), "result_category"] = "CRITICAL"

        # Clip extreme outliers (data quality)
        df["result_value"] = df["result_value"].clip(
            lower=df["reference_range_low"] * 0.1 if "reference_range_low" in df else None,
            upper=df["reference_range_high"] * 10 if "reference_range_high" in df else None
        )

        df["transformed_at"] = datetime.utcnow()
        df["data_layer"] = "SILVER"

        self.transformation_stats["labs"] = {
            "input": len(raw_records), "output": len(df),
            "critical_values": int(df["is_critical"].sum()),
            "abnormal_pct": f"{df['result_category'].eq('ABNORMAL').mean()*100:.1f}%"
        }
        logger.info(f"  ✓ Transformed {len(df)} lab records | Critical: {df['is_critical'].sum()}")
        return df

    # ─── ICU Vitals Transformations ────────────────────────────────────────

    def transform_icu_vitals(self, raw_records: List[Dict]) -> pd.DataFrame:
        logger.info(f"Transforming {len(raw_records)} ICU vitals records...")
        df = pd.DataFrame(raw_records)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["patient_id", "timestamp"])

        # Rolling 5-minute window stats per patient
        df["hr_rolling_avg"] = (
            df.groupby("patient_id")["heart_rate"]
            .transform(lambda x: x.rolling(window=10, min_periods=1).mean())
            .round(1)
        )

        # MAP validation
        df["map_calculated"] = (
            (df["systolic_bp"] + 2 * df["diastolic_bp"]) / 3
        ).round(1)

        # Vital sign status
        df["vitals_status"] = "STABLE"
        df.loc[df["alert_triggered"], "vitals_status"] = "ALERT"
        df.loc[df["spo2"] < 94, "vitals_status"] = "WATCH"

        df["transformed_at"] = datetime.utcnow()
        df["data_layer"] = "SILVER"

        self.transformation_stats["icu_vitals"] = {
            "input": len(raw_records), "output": len(df),
            "alerts_triggered": int(df["alert_triggered"].sum()),
            "alert_rate_pct": f"{df['alert_triggered'].mean()*100:.2f}%"
        }
        logger.info(f"  ✓ Transformed {len(df)} ICU records | Alerts: {df['alert_triggered'].sum()}")
        return df

    # ─── Unified Clinical Mart ─────────────────────────────────────────────

    def build_patient_encounter_mart(
        self,
        patients_df: pd.DataFrame,
        encounters_df: pd.DataFrame,
        labs_df: pd.DataFrame,
        billing_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Build the gold layer patient-encounter mart for analytics."""
        logger.info("Building patient-encounter analytics mart...")

        # Join patients + encounters
        mart = encounters_df.merge(
            patients_df[["patient_id", "gender", "age_years", "age_group",
                          "insurance_type", "zip_code"]],
            on="patient_id", how="left"
        )

        # Aggregate labs per encounter
        if len(labs_df) > 0:
            lab_agg = labs_df.groupby("encounter_id").agg(
                lab_count=("lab_result_id", "count"),
                critical_lab_count=("is_critical", "sum"),
                abnormal_lab_count=("result_category", lambda x: (x == "ABNORMAL").sum()),
            ).reset_index()
            mart = mart.merge(lab_agg, on="encounter_id", how="left")
        else:
            mart["lab_count"] = 0
            mart["critical_lab_count"] = 0

        # Aggregate billing per encounter
        if len(billing_df) > 0:
            bill_agg = billing_df.groupby("encounter_id").agg(
                total_charges=("charge_amount", "sum"),
                total_paid=("paid_amount", "sum"),
                claim_count=("claim_id", "count"),
            ).reset_index()
            mart = mart.merge(bill_agg, on="encounter_id", how="left")
        else:
            mart["total_charges"] = 0.0

        mart["data_layer"] = "GOLD"
        mart["mart_created_at"] = datetime.utcnow()

        logger.info(f"  ✓ Patient-encounter mart: {len(mart)} rows")
        return mart

    def get_stats(self) -> Dict:
        return self.transformation_stats
