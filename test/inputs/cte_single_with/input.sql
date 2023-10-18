with cte as (
    select max(a) as a_max
    from t
)
select a_max
from cte
