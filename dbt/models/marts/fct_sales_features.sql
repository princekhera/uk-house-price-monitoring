-- One row per matched market sale: the modelling table.
select
    p.transaction_id,
    p.sale_date,
    date_trunc(p.sale_date, month)                       as sale_month,
    p.price,
    p.property_type,
    p.old_new,
    p.tenure,
    p.district,
    regexp_extract(p.postcode, r'^([A-Z]{1,2})')         as postcode_area,
    split(p.postcode, ' ')[safe_offset(0)]               as postcode_district,
    m.lad_code,
    case
        when m.lad_code like 'W06%' then 'Wales'
        else coalesce(r.region, 'Unknown')
    end                                                  as region,
    m.floor_area_m2,
    m.habitable_rooms,
    m.energy_efficiency,
    m.current_energy_rating,
    m.construction_age_band,
    m.built_form,
    m.main_fuel,
    m.match_tier,
    date_diff(p.sale_date, m.lodgement_date, day)        as epc_age_days
from {{ ref('stg_price_paid') }} p
join {{ ref('int_sales_epc_matched') }} m using (transaction_id)
left join {{ ref('stg_lad_region') }} r on m.lad_code = r.lad_code
where p.price between {{ var('min_price') }} and {{ var('max_price') }}
  and m.floor_area_m2 between 15 and 1000
