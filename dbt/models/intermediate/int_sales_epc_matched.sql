-- Match each sale to the most recent EPC lodged ON OR BEFORE the sale date
-- (an EPC lodged after the sale would leak future information).
-- tier 1 = exact normalised address, tier 2 = EPC address starts with the
-- Price Paid address (handles trailing locality/town in EPC address lines).
with candidates as (
    select
        p.transaction_id,
        e.* except (postcode, addr1_norm, addr12_norm, addr_full_norm),
        case
            when p.addr_norm in (e.addr1_norm, e.addr12_norm) then 1
            else 2
        end as match_tier
    from {{ ref('stg_price_paid') }} p
    join {{ ref('stg_epc') }} e
      on p.postcode = e.postcode
    where e.lodgement_date <= p.sale_date
      and p.addr_norm != ''
      and (
            p.addr_norm in (e.addr1_norm, e.addr12_norm)
         or starts_with(e.addr_full_norm, concat(p.addr_norm, ' '))
      )
)
select * except (rn)
from (
    select
        *,
        row_number() over (
            partition by transaction_id
            order by match_tier, lodgement_date desc, lmk_key
        ) as rn
    from candidates
)
where rn = 1
