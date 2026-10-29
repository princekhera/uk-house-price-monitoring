select
    {{ var('lad_code_col') }}    as lad_code,
    {{ var('region_name_col') }} as region
from {{ source('raw', 'lad_region_raw') }}
