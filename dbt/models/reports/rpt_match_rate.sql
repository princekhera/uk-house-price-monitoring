-- How much of the market survives the EPC join, by year and region.
-- Report this in the README: unmatched sales are a selection-bias risk.
with sales as (
    select transaction_id, extract(year from sale_date) as yr, property_type
    from {{ ref('stg_price_paid') }}
)
select
    s.yr,
    s.property_type,
    count(*)                                            as n_sales,
    countif(m.transaction_id is not null)               as n_matched,
    round(safe_divide(countif(m.transaction_id is not null), count(*)), 3) as match_rate,
    countif(m.match_tier = 1)                           as n_exact,
    countif(m.match_tier = 2)                           as n_prefix
from sales s
left join {{ ref('int_sales_epc_matched') }} m using (transaction_id)
group by 1, 2
order by 1, 2
