"""
Configuration management for Clinical ETL Platform.
Loads from environment variables with sensible defaults for local demo.
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SnowflakeConfig:
    account: str = os.getenv("SNOWFLAKE_ACCOUNT", "demo_account")
    user: str = os.getenv("SNOWFLAKE_USER", "demo_user")
    password: str = os.getenv("SNOWFLAKE_PASSWORD", "demo_password")
    database: str = os.getenv("SNOWFLAKE_DATABASE", "CLINICAL_DW")
    warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE", "CLINICAL_WH")
    schema: str = os.getenv("SNOWFLAKE_SCHEMA", "RAW")
    role: str = os.getenv("SNOWFLAKE_ROLE", "CLINICAL_ETL_ROLE")


@dataclass
class SparkConfig:
    app_name: str = "ClinicalETLPlatform"
    master: str = os.getenv("SPARK_MASTER", "local[*]")
    executor_memory: str = os.getenv("SPARK_EXECUTOR_MEMORY", "4g")
    driver_memory: str = os.getenv("SPARK_DRIVER_MEMORY", "2g")
    max_result_size: str = "2g"
    shuffle_partitions: int = 200


@dataclass
class AirflowConfig:
    base_url: str = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
    username: str = os.getenv("AIRFLOW_USERNAME", "admin")
    password: str = os.getenv("AIRFLOW_PASSWORD", "admin")
    dag_run_interval: str = "*/30 * * * *"  # Every 30 minutes


@dataclass
class SourceSystemConfig:
    """Configuration for each of the 8 source systems."""
    ehr: dict = field(default_factory=lambda: {
        "name": "EHR_SYSTEM",
        "type": "rest_api",
        "base_url": os.getenv("EHR_BASE_URL", "http://localhost:8081"),
        "api_key": os.getenv("EHR_API_KEY", "demo_key"),
        "format": "fhir_json",
        "batch_size": 1000,
        "daily_records": 50000,
    })
    lab: dict = field(default_factory=lambda: {
        "name": "LAB_SYSTEM",
        "type": "sftp",
        "host": os.getenv("LAB_SFTP_HOST", "lab-sftp.hospital.local"),
        "port": 22,
        "username": os.getenv("LAB_SFTP_USER", "lab_etl"),
        "password": os.getenv("LAB_SFTP_PASS", "demo_pass"),
        "remote_path": "/exports/daily/",
        "format": "csv_hl7",
        "daily_records": 15000,
    })
    billing: dict = field(default_factory=lambda: {
        "name": "BILLING_SYSTEM",
        "type": "database",
        "connection_string": os.getenv("BILLING_DB_URL", "sqlite:///demo_billing.db"),
        "schema": "billing",
        "format": "sql",
        "daily_records": 8000,
    })
    scheduling: dict = field(default_factory=lambda: {
        "name": "SCHEDULING_SYSTEM",
        "type": "rest_api",
        "base_url": os.getenv("SCHEDULING_URL", "http://localhost:8082"),
        "format": "json",
        "daily_records": 12000,
    })
    pharmacy: dict = field(default_factory=lambda: {
        "name": "PHARMACY_SYSTEM",
        "type": "sftp",
        "host": os.getenv("PHARMACY_HOST", "pharmacy-sftp.hospital.local"),
        "format": "csv",
        "daily_records": 20000,
    })
    radiology: dict = field(default_factory=lambda: {
        "name": "RADIOLOGY_SYSTEM",
        "type": "rest_api",
        "base_url": os.getenv("RADIOLOGY_URL", "http://localhost:8083"),
        "format": "dicom_json",
        "daily_records": 3000,
    })
    icu: dict = field(default_factory=lambda: {
        "name": "ICU_MONITOR_SYSTEM",
        "type": "kafka",
        "bootstrap_servers": os.getenv("KAFKA_SERVERS", "localhost:9092"),
        "topic": "icu.vitals.stream",
        "format": "timeseries_json",
        "daily_records": 500000,
    })
    hr: dict = field(default_factory=lambda: {
        "name": "HR_SYSTEM",
        "type": "database",
        "connection_string": os.getenv("HR_DB_URL", "sqlite:///demo_hr.db"),
        "format": "sql",
        "daily_records": 500,
    })


@dataclass
class PipelineConfig:
    """Master pipeline configuration."""
    snowflake: SnowflakeConfig = field(default_factory=SnowflakeConfig)
    spark: SparkConfig = field(default_factory=SparkConfig)
    airflow: AirflowConfig = field(default_factory=AirflowConfig)
    sources: SourceSystemConfig = field(default_factory=SourceSystemConfig)

    # Pipeline behavior
    use_demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    output_dir: str = os.getenv("OUTPUT_DIR", "./outputs")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_data_masking: bool = True
    enable_quality_gates: bool = True
    quality_threshold: float = 0.95  # Fail if quality < 95%

    # Performance targets
    target_latency_minutes: int = 22
    sla_data_quality: float = 0.998


# Singleton
config = PipelineConfig()
