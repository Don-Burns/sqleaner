WITH cte AS (
    SELECT MAX(a) AS a_max
    FROM t
)
SELECT a_max
FROM cte
;
