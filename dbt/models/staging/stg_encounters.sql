-- models/staging/stg_encounters.sql

{{ config(materialized='view', schema='STAGING') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_encounters') }}
),

renamed AS (
    SELECT
        encounter_id,
        patient_id,
        UPPER(encounter_type)                           AS encounter_type,
        CAST(admit_datetime AS TIMESTAMP)               AS admit_datetime,
        CAST(discharge_datetime AS TIMESTAMP)           AS discharge_datetime,
        primary_diagnosis_icd10                         AS icd10_code,
        attending_physician_id,
        UPPER(department)                               AS department,
        facility_id,
        CAST(los_days AS FLOAT)                         AS los_days,
        UPPER(los_risk)                                 AS los_risk,
        drg_code,
        year_month,
        CAST(encounter_hours AS FLOAT)                  AS encounter_hours,
        source_system,
        data_layer,
        -- Derived flags
        CASE WHEN los_days > 14 THEN TRUE ELSE FALSE END    AS is_extended_stay,
        CASE WHEN encounter_type = 'ED' THEN TRUE ELSE FALSE END AS is_ed_visit,
        CURRENT_TIMESTAMP()                             AS dbt_loaded_at
    FROM source
    WHERE encounter_id IS NOT NULL
)

SELECT * FROM renamed
