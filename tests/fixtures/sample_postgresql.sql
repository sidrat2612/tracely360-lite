CREATE TABLE public.orders (
    id INT NOT NULL PRIMARY KEY,
    total INT NOT NULL
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
END;
$$;

CREATE TRIGGER orders_after_insert
AFTER INSERT ON public.orders
FOR EACH ROW
EXECUTE FUNCTION public.get_order_total(NEW.id);