SELECT
    t.id
    , d.val
FROM test AS t
JOIN dim_tbl AS d ON t.id = d.id
;
