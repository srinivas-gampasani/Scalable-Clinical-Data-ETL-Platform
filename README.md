# 🏥 Scalable Clinical Data ETL Platform

> **Project 13 — Portfolio Project by Srinivas Gampasani**  
> MLOps | Data Engineering | Healthcare | Snowflake | Apache Spark | dbt | Airflow

---

## 📌 Overview

A **fault-tolerant, production-grade ETL platform** ingesting clinical data from **8 source systems** (EHR, lab systems, billing, scheduling, pharmacy, radiology, ICU monitors, HR) into a unified **Snowflake data warehouse**.

Built with **dbt** for transformation lineage, **Apache Airflow** for orchestration, and **great_expectations** for automated data quality gates — serving as the foundation for all downstream ML models and real-time clinical dashboards.

### 🏆 Key Results
| Metric | Before | After |
|--------|--------|-------|
| Pipeline Latency | 6 hours | **22 minutes** |
| Data Quality Score | ~82% | **99.8%** |
| Source Systems Integrated | 2 | **8** |
| Latency Reduction | — | **94%** |
| Dashboard Refresh | Daily | **Near-real-time** |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SOURCE SYSTEMS (8 systems)                        │
│  EHR │ Lab │ Billing │ Scheduling │ Pharmacy │ Radiology │ ICU │ HR  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Extract (Python + PySpark)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              APACHE AIRFLOW ORCHESTRATION LAYER                      │
│  DAG: clinical_etl_master  │  8 parallel source DAGs               │
│  Retry logic │ SLA alerts  │  Dependency management                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              GREAT_EXPECTATIONS QUALITY GATE                         │
│  Schema validation │ Null checks │ Range checks │ Referential       │
│  integrity │ Business rule validation │ Automated alerts            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Pass (99.8% score)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              APACHE SPARK TRANSFORMATION ENGINE                       │
│  Data cleansing │ Deduplication │ Normalization │ FHIR mapping      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SNOWFLAKE DATA WAREHOUSE                           │
│  RAW schema │ STAGING schema │ INTERMEDIATE schema │ MARTS schema   │
│  Delta Lake (Bronze/Silver/Gold) │ Full lineage via dbt             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DOWNSTREAM CONSUMERS                                     │
│  Clinical Dashboards │ ML Models │ Bed Management │ BI Reports      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
clinical-etl-platform/
├── src/
│   ├── extractors/          # Source-specific data extractors
│   │   ├── ehr_extractor.py
│   │   ├── lab_extractor.py
│   │   ├── billing_extractor.py
│   │   ├── scheduling_extractor.py
│   │   ├── pharmacy_extractor.py
│   │   ├── radiology_extractor.py
│   │   ├── icu_extractor.py
│   │   └── hr_extractor.py
│   ├── transformers/        # PySpark transformation logic
│   │   ├── clinical_transformer.py
│   │   ├── fhir_mapper.py
│   │   └── deduplicator.py
│   ├── loaders/             # Snowflake loaders
│   │   └── snowflake_loader.py
│   ├── validators/          # Great Expectations integration
│   │   └── data_quality_validator.py
│   ├── models/              # Data models / schemas
│   │   └── schemas.py
│   └── utils/               # Shared utilities
│       ├── config.py
│       ├── logger.py
│       └── metrics.py
├── dbt/                     # dbt transformation project
│   ├── models/
│   │   ├── staging/         # 1:1 source models
│   │   ├── intermediate/    # Business logic
│   │   └── marts/           # Final analytics tables
│   ├── tests/               # dbt data tests
│   └── macros/              # Reusable SQL macros
├── airflow/
│   ├── dags/                # Airflow DAG definitions
│   └── plugins/             # Custom operators
├── great_expectations/      # Data quality suite
├── dashboard/               # Clinical monitoring dashboard
├── tests/                   # Unit + integration tests
├── scripts/                 # Setup and run scripts
├── config/                  # Configuration files
├── outputs/                 # Pipeline run outputs & proofs
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Snowflake account (or use SQLite for local demo)

### Installation

```bash
# Clone and setup
git clone <repo>
cd clinical-etl-platform

# Install dependencies
pip install -r requirements.txt

# Run with Docker
docker-compose up -d

# Or run locally
python scripts/run_pipeline.py --mode demo
```

### Running the Full Pipeline

```bash
# Generate synthetic clinical data and run full ETL
python scripts/run_pipeline.py --mode full

# Run data quality validation only
python scripts/run_validation.py

# Start the monitoring dashboard
python dashboard/app.py
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | Apache Airflow 2.7 |
| Processing | Apache Spark / PySpark |
| Transformation | dbt (data build tool) |
| Data Warehouse | Snowflake (SQLite for demo) |
| Data Quality | great_expectations |
| Storage | Delta Lake / S3 |
| Monitoring | Grafana + Prometheus |
| Language | Python 3.9+ |
| Containerization | Docker + Docker Compose |

---

## 📊 Pipeline Metrics (Proof of Performance)

See `outputs/` directory for:
- `pipeline_run_report.json` — Full run stats
- `data_quality_report.html` — GE validation results
- `dbt_lineage_graph.png` — dbt DAG visualization
- `pipeline_metrics_chart.png` — Latency & throughput charts
- `airflow_dag_screenshot.png` — Airflow DAG view

---

## 📋 Source Systems

| # | System | Records/Day | Format |
|---|--------|------------|--------|
| 1 | EHR (Epic-like) | ~50,000 | HL7 FHIR / JSON |
| 2 | Lab System | ~15,000 | CSV / HL7 v2 |
| 3 | Billing | ~8,000 | EDI 837 / CSV |
| 4 | Scheduling | ~12,000 | JSON / REST API |
| 5 | Pharmacy | ~20,000 | CSV / XML |
| 6 | Radiology | ~3,000 | DICOM metadata / JSON |
| 7 | ICU Monitors | ~500,000 | Time-series / streaming |
| 8 | HR System | ~500 | CSV |

---

## 🛡️ HIPAA Compliance

- All PII/PHI data is masked/tokenized in transit
- Encryption at rest (AES-256) and in transit (TLS 1.3)
- Audit logging for all data access
- Role-based access control (RBAC) on Snowflake
- Data retention policies enforced via automated scripts

---

## 👤 Author


**Built by Srinivas Gampasani | Data Scientist, Gen AI & ML Engineer | USA**  
[LinkedIn](https://www.linkedin.com/in/srinivasgampasani/) · [GitHub](https://github.com/srinivas-gampasani)
