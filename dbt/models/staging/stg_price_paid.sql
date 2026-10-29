-- Standard-price residential sales only (category A). Category B covers
-- repossessions, buy-to-let and other non-market transfers.
select
    transaction_id,
    price,
    date(safe.parse_datetime('%Y-%m-%d %H:%M', date_of_transfer)) as sale_date,
    upper(trim(postcode))                                          as postcode,
    property_type,                     -- D/S/T/F (O = other, dropped)
    old_new,                           -- Y = new build
    duration                            as tenure,  -- F/L
    {{ norm_addr("concat(coalesce(saon,''), ' ', coalesce(paon,''), ' ', coalesce(street,''))") }} as addr_norm,
    district,
    county
from {{ source('raw', 'price_paid') }}
where ppd_category_type = 'A'
  and property_type in ('D', 'S', 'T', 'F')
  and duration in ('F', 'L')
  and postcode is not null
  and coalesce(record_status, 'A') = 'A'
