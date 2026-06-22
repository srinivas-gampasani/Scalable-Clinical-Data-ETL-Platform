-- models/staging/stg_patients.sql
-- Staging: 1:1 source copy with type casting and basic renaming

{{ config(materialized='view', schema='STAGING') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_patients') }}
),

renamed AS (
    SELECT
        patient_id,
        mrn,
        gender,
        CAST(dob AS DATE)                           AS date_of_birth,
        CAST(age_years AS INTEGER)                  AS age_years,
        age_group,
        zip_code,
        UPPER(insurance_type)                       AS insurance_type,
        primary_physician_id,
        source_system,
        CAST(extracted_at AS TIMESTAMP)             AS extracted_at,
        CAST(transformed_at AS TIMESTAMP)           AS transformed_at,
        data_layer,
        -- Audit columns
        CURRENT_TIMESTAMP()                         AS dbt_loaded_at,
        '{{ invocation_id }}'                       AS dbt_run_id
    FROM source
)

SELECT * FROM renamed
