-- macros/clinical_helpers.sql
-- Reusable dbt macros for clinical data transformations

{% macro age_group(age_col) %}
  CASE
    WHEN {{ age_col }} BETWEEN 0  AND 17  THEN '0-17'
    WHEN {{ age_col }} BETWEEN 18 AND 34  THEN '18-34'
    WHEN {{ age_col }} BETWEEN 35 AND 49  THEN '35-49'
    WHEN {{ age_col }} BETWEEN 50 AND 64  THEN '50-64'
    WHEN {{ age_col }} BETWEEN 65 AND 79  THEN '65-79'
    WHEN {{ age_col }} >= 80              THEN '80+'
    ELSE 'UNKNOWN'
  END
{% endmacro %}


{% macro los_risk(los_col) %}
  CASE
    WHEN {{ los_col }} > 14 THEN 'CRITICAL'
    WHEN {{ los_col }} > 7  THEN 'EXTENDED'
    ELSE                         'NORMAL'
  END
{% endmacro %}


{% macro encounter_risk_score(los_col, critical_lab_col, abnormal_lab_col) %}
  CASE
    WHEN {{ los_col }} > 14 AND {{ critical_lab_col }} > 0 THEN 'HIGH'
    WHEN {{ los_col }} > 7  OR  {{ abnormal_lab_col }} > 3 THEN 'MEDIUM'
    ELSE 'LOW'
  END
{% endmacro %}


{% macro collection_rate(paid_col, charge_col) %}
  CASE
    WHEN {{ charge_col }} > 0
    THEN ROUND({{ paid_col }} / {{ charge_col }} * 100, 2)
    ELSE NULL
  END
{% endmacro %}


{% macro is_critical_lab(flag_col) %}
  CASE WHEN {{ flag_col }} IN ('HH', 'LL') THEN TRUE ELSE FALSE END
{% endmacro %}


{% macro date_diff_hours(start_col, end_col) %}
  DATEDIFF('hour', {{ start_col }}::TIMESTAMP, {{ end_col }}::TIMESTAMP)
{% endmacro %}


{% macro mask_phi(col) %}
  '***PHI_MASKED***'
{% endmacro %}


{% macro generate_surrogate_key(fields) %}
  MD5(CONCAT_WS('|', {% for f in fields %}{{ f }}{% if not loop.last %}, {% endif %}{% endfor %}))
{% endmacro %}
