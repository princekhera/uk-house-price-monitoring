select
    lmk_key,
    upper(trim(postcode))                                        as postcode,
    safe_cast(lodgement_date as date)                            as lodgement_date,
    {{ norm_addr("address1") }}                                  as addr1_norm,
    {{ norm_addr("concat(coalesce(address1,''), ' ', coalesce(address2,''))") }} as addr12_norm,
    {{ norm_addr("concat(coalesce(address1,''), ' ', coalesce(address2,''), ' ', coalesce(address3,''))") }} as addr_full_norm,
    local_authority                                              as lad_code,
    property_type                                                as epc_property_type,
    nullif(nullif(built_form, 'Not Recorded'), 'NO DATA!')        as built_form,
    current_energy_rating,
    safe_cast(current_energy_efficiency as int64)                as energy_efficiency,
    safe_cast(total_floor_area as float64)                       as floor_area_m2,
    safe_cast(number_habitable_rooms as int64)                   as habitable_rooms,
    case
        when regexp_contains(construction_age_band, r'^\d{4}$') then
            case when safe_cast(construction_age_band as int64) >= 2007 then '2007 onwards'
                 else 'year-coded pre-2007' end
        when regexp_contains(construction_age_band, r'2007|2012') then '2007 onwards'
        when regexp_contains(construction_age_band, r'\d{4}-\d{4}|before 1900') then
            regexp_replace(construction_age_band, r'^England and Wales: ', '')
        else null   -- NO DATA!, INVALID!, blanks
    end                                                            as construction_age_band,
    case
        when lower(main_fuel) like '%mains gas%'                                   then 'mains gas'
        when lower(main_fuel) like '%electric%'                                    then 'electricity'
        when lower(main_fuel) like '%lpg%'                                         then 'lpg'
        when regexp_contains(lower(main_fuel), r'\boil\b')                         then 'oil'
        when regexp_contains(lower(main_fuel), r'coal|wood|anthracite|smokeless|biomass|mineral') then 'solid fuel'
        when lower(main_fuel) like 'to be used only%'                              then null
        when main_fuel is null or main_fuel in ('NO DATA!', 'INVALID!')            then null
        else 'other'
    end                                                            as main_fuel
from {{ source('raw', 'epc') }}
where postcode is not null
  and safe_cast(total_floor_area as float64) > 0
