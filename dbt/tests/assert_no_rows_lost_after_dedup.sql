-- Silver must contain exactly one row per distinct User_ID found in bronze.
with b as (select count(distinct upper(trim(User_ID))) as n from {{ source('bronze', 'ai_usage_raw') }}),
     f as (select count(*) as n from {{ ref('fct_ai_usage') }})
select b.n as bronze_users, f.n as fact_rows
from b cross join f
where b.n <> f.n
