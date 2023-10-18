with cte as (
    select id, max(a) as a_max
    from t
),
cte2 as (
    select id, max(a) as a_max
    from t
)
select
    cte1.a_max
    , cte2.a_max
from cte as cte1
join cte2 as cte2 on cte1.id = cte2.id
