with source_data as (
    select
        order_id,
        customer_id,
        cast(total_price as float64) as total_price,
        cast(order_date as date) as order_date,
        status
    from {{ source('raw_data', 'daily_orders') }}
)

select * from source_data