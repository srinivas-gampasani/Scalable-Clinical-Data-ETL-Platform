-- models/intermediate/int_patient_encounters.sql
-- Joins patients + encounters with business logic

{{ config(materialized='table', schema='INTERMEDIATE') }}

WITH patients AS (
    SELECT * FROM {{ ref('stg_patients') }}
),

encounters AS (
    SELECT * FROM {{ ref('stg_encounters') }}
),

labs_agg AS (
    SELECT
        encounter_id,
        COUNT(*)                                    AS total_lab_orders,
        SUM(CASE WHEN is_critical = 1 THEN 1 ELSE 0 END) AS critical_lab_count,
        SUM(CASE WHEN result_category = 'ABNORMAL' THEN 1 ELSE 0 END) AS abnormal_lab_count,
        AVG(tat_hours)                              AS avg_lab_tat_hours
    FROM {{ source('raw', 'raw_labs') }}
    GROUP BY 1
),

billing_agg AS (
    SELECT
        encounter_id,
        SUM(charge_amount)                          AS total_charges,
        SUM(COALESCE(paid_amount, 0))               AS total_paid,
        COUNT(*)                                    AS claim_count,
        SUM(CASE WHEN claim_status = 'DENIED' THEN 1 ELSE 0 END) AS denied_claims
    FROM {{ source('raw', 'raw_billing') }}
    GROUP BY 1
),

joined AS (
    SELECT
        e.encounter_id,
        e.patient_id,
        e.encounter_type,
        e.admit_datetime,
        e.discharge_datetime,
        e.icd10_code,
        e.department,
        e.facility_id,
        e.los_days,
        e.los_risk,
        e.is_extended_stay,
        e.is_ed_visit,
        e.year_month,

        -- Patient attributes
        p.gender,
        p.age_years,
        p.age_group,
        p.insurance_type,
        p.zip_code,

        -- Lab metrics
        COALESCE(l.total_lab_orders, 0)             AS total_lab_orders,
        COALESCE(l.critical_lab_count, 0)           AS critical_lab_count,
        COALESCE(l.abnormal_lab_count, 0)           AS abnormal_lab_count,
        l.avg_lab_tat_hours,

        -- Financial metrics
        COALESCE(b.total_charges, 0)                AS total_charges,
        COALESCE(b.total_paid, 0)                   AS total_paid,
        COALESCE(b.claim_count, 0)                  AS claim_count,
        COALESCE(b.denied_claims, 0)                AS denied_claims,
        CASE
            WHEN b.total_charges > 0
            THEN ROUND(b.total_paid / b.total_charges * 100, 2)
            ELSE NULL
        END                                         AS collection_rate_pct,

        -- Composite risk score
        CASE
            WHEN e.los_days > 14 AND l.critical_lab_count > 0 THEN 'HIGH'
            WHEN e.los_days > 7 OR l.abnormal_lab_count > 3 THEN 'MEDIUM'
            ELSE 'LOW'
        END                                         AS encounter_risk_score,

        CURRENT_TIMESTAMP()                         AS dbt_loaded_at

    FROM encounters e
    LEFT JOIN patients p ON e.patient_id = p.patient_id
    LEFT JOIN labs_agg l ON e.encounter_id = l.encounter_id
    LEFT JOIN billing_agg b ON e.encounter_id = b.encounter_id
)

SELECT * FROM joined
