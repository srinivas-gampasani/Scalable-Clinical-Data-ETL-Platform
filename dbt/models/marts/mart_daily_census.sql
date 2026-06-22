-- models/marts/clinical_ops/mart_daily_census.sql
-- Gold layer: Daily hospital census for clinical operations dashboard

{{ config(
    materialized='table',
    schema='MARTS',
    post_hook="GRANT SELECT ON {{ this }} TO ROLE ANALYST_ROLE"
) }}

WITH encounters AS (
    SELECT * FROM {{ ref('int_patient_encounters') }}
),

daily_census AS (
    SELECT
        DATE(admit_datetime)                            AS census_date,
        facility_id,
        department,
        encounter_type,

        -- Volume metrics
        COUNT(DISTINCT encounter_id)                    AS encounter_count,
        COUNT(DISTINCT patient_id)                      AS unique_patients,

        -- LOS metrics
        AVG(los_days)                                   AS avg_los_days,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY los_days)
                                                        AS median_los_days,
        MAX(los_days)                                   AS max_los_days,
        SUM(CASE WHEN is_extended_stay THEN 1 ELSE 0 END) AS extended_stay_count,

        -- Risk stratification
        SUM(CASE WHEN encounter_risk_score = 'HIGH' THEN 1 ELSE 0 END)   AS high_risk_count,
        SUM(CASE WHEN encounter_risk_score = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_risk_count,
        SUM(CASE WHEN encounter_risk_score = 'LOW' THEN 1 ELSE 0 END)    AS low_risk_count,

        -- Financial
        SUM(total_charges)                              AS total_charges,
        SUM(total_paid)                                 AS total_paid,
        AVG(collection_rate_pct)                        AS avg_collection_rate,

        -- Payer mix
        COUNT(CASE WHEN insurance_type = 'MEDICARE' THEN 1 END) AS medicare_count,
        COUNT(CASE WHEN insurance_type = 'MEDICAID' THEN 1 END) AS medicaid_count,
        COUNT(CASE WHEN insurance_type = 'SELF_PAY' THEN 1 END) AS self_pay_count,

        -- Demographics
        AVG(age_years)                                  AS avg_patient_age,
        COUNT(CASE WHEN age_years >= 65 THEN 1 END)    AS senior_patient_count,

        CURRENT_TIMESTAMP()                             AS dbt_loaded_at

    FROM encounters
    GROUP BY 1, 2, 3, 4
)

SELECT * FROM daily_census
ORDER BY census_date DESC, facility_id, department
