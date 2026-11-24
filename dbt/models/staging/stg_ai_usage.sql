-- One row per user, typed and cleaned by the PySpark silver layer.
-- Staging only selects/renames and keeps the columns analytics needs.
select
    user_id,
    age,
    gender,
    country,
    user_type,
    education_level,
    profession,
    monthly_income,
    ai_tool,
    ai_purpose,
    ai_usage_hours_per_day,
    tasks_performed,
    num_tasks,
    monthly_ai_cost,
    productivity_score,
    accuracy_rating,
    satisfaction_score,
    time_saved_hours_per_week,
    work_or_study_hours_per_day,
    would_recommend,
    dq_issue_count,
    _processed_at as processed_at
from {{ source('silver', 'ai_usage_clean') }}
