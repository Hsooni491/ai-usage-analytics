-- Business logic: bands, tiers, job families and efficiency metrics.
with base as (
    select * from {{ ref('stg_ai_usage') }}
)

select
    base.*,

    -- Job family from the multilingual free-text profession
    {{ profession_category('profession') }} as profession_category,

    case
        when age is null then 'Unknown'
        when age < 18 then 'Under 18'
        when age < 25 then '18-24'
        when age < 35 then '25-34'
        when age < 45 then '35-44'
        when age < 55 then '45-54'
        else '55+'
    end as age_group,

    case
        when ai_usage_hours_per_day is null then 'Unknown'
        when ai_usage_hours_per_day < 1 then '< 1 h'
        when ai_usage_hours_per_day < 2 then '1-2 h'
        when ai_usage_hours_per_day < 4 then '2-4 h'
        when ai_usage_hours_per_day < 6 then '4-6 h'
        else '6+ h'
    end as usage_band,
    case
        when ai_usage_hours_per_day is null then 9
        when ai_usage_hours_per_day < 1 then 1
        when ai_usage_hours_per_day < 2 then 2
        when ai_usage_hours_per_day < 4 then 3
        when ai_usage_hours_per_day < 6 then 4
        else 5
    end as usage_band_order,

    case
        when monthly_ai_cost is null then 'Unknown'
        when monthly_ai_cost = 0 then 'Free'
        when monthly_ai_cost <= 20 then 'Standard ($1-20)'
        else 'Premium (>$20)'
    end as plan_tier,
    case when monthly_ai_cost > 0 then 1 else 0 end as is_paid_user,

    case
        when monthly_income is null then 'Unknown'
        when monthly_income < 500 then '< $500'
        when monthly_income < 2000 then '$500-2k'
        when monthly_income < 5000 then '$2k-5k'
        else '$5k+'
    end as income_band,

    case would_recommend when 'Yes' then 1 else 0 end as is_promoter,
    case would_recommend when 'No'  then 1 else 0 end as is_detractor,

    -- Efficiency metrics
    ai_usage_hours_per_day * 7                                          as ai_hours_per_week,
    {{ safe_divide('time_saved_hours_per_week', 'ai_usage_hours_per_day * 7') }}
                                                                        as hours_saved_per_ai_hour,
    {{ safe_divide('ai_usage_hours_per_day', 'work_or_study_hours_per_day') }}
                                                                        as ai_share_of_workday,
    case when monthly_ai_cost > 0
         then {{ safe_divide('monthly_ai_cost', 'time_saved_hours_per_week * ' ~ var('weeks_per_month')) }}
    end                                                                 as cost_per_hour_saved

from base
