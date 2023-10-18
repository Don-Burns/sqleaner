WITH cte AS (
    SELECT
        id
        , MAX(a) AS a_max
    FROM t
),
cte2 AS (
    SELECT
        id
        , MAX(a) AS a_max
    FROM t
)
SELECT
    cte1.a_max
    , cte2.a_max
FROM cte AS cte1
JOIN cte2 AS cte2 ON cte1.id = cte2.id
;
