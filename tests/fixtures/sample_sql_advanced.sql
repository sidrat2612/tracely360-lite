CREATE TABLE sales.orders (
    id INT NOT NULL PRIMARY KEY,
    total INT NOT NULL
);

CREATE MATERIALIZED VIEW sales.mv_orders AS
SELECT *
FROM sales.orders;

CREATE FUNCTION sales.refresh_order_totals()
RETURNS INT
LANGUAGE SQL
AS $$
    SELECT COUNT(*)
    FROM sales.orders;
$$;

CREATE PROCEDURE sales.recompute()
LANGUAGE SQL
AS $$
    CALL sales.refresh_order_totals();
$$;