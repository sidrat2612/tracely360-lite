CREATE TABLE public.orders (
    id INT NOT NULL PRIMARY KEY,
    total INT NOT NULL
);

CREATE TABLE public.audit_log (
    order_id INT NOT NULL
);

CREATE OR REPLACE FUNCTION public.get_order_total(p_id INT)
RETURNS INT
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN (
        SELECT total
        FROM public.orders
        WHERE id = p_id
    );
END;
$$;

CREATE OR REPLACE PROCEDURE public.create_order(p_total INT)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.orders (id, total)
    VALUES (1, p_total);
    PERFORM public.get_order_total(1);
    CALL public.rebuild_totals();
END;
$$;

CREATE OR REPLACE PROCEDURE public.rebuild_totals()
LANGUAGE plpgsql
AS $$
BEGIN
    WITH latest AS (
        SELECT id
        FROM public.orders
    )
    PERFORM public.get_order_total(id) FROM latest;
END;
$$;

CREATE OR REPLACE FUNCTION public.audit_orders()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.audit_log(order_id)
    VALUES (NEW.id);
    EXECUTE format('SELECT * FROM %I', 'audit_log');
    RETURN NEW;
END;
$$;

CREATE MATERIALIZED VIEW public.mv_orders AS
WITH recent AS (
    SELECT *
    FROM public.orders
)
SELECT * FROM recent;

CREATE TRIGGER orders_after_insert
AFTER INSERT ON public.orders
FOR EACH ROW
EXECUTE FUNCTION public.audit_orders(NEW.id);