-- Sample SQL fixture for tracely360 language tests
-- Covers: tables, view, stored procedure, function, trigger

CREATE TABLE users (
    id   INT          NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255)
);

CREATE TABLE orders (
    id         INT  NOT NULL PRIMARY KEY,
    user_id    INT  NOT NULL,
    total      DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- View joining two tables
CREATE VIEW active_user_orders AS
SELECT u.id, u.name, o.id AS order_id, o.total
FROM users u
JOIN orders o ON o.user_id = u.id;

-- Function: returns total spend for a user (PostgreSQL $$ style)
CREATE FUNCTION get_user_total(p_user_id INT)
RETURNS DECIMAL
LANGUAGE SQL
AS $$
    SELECT SUM(total)
    FROM orders
    WHERE user_id = p_user_id;
$$;

-- Stored procedure (PostgreSQL $$ style)
CREATE PROCEDURE create_order(IN p_user_id INT, IN p_total DECIMAL)
LANGUAGE SQL
AS $$
    INSERT INTO orders (user_id, total)
    VALUES (p_user_id, p_total);
    SELECT get_user_total(p_user_id);
$$;

-- Trigger: fires after an order is inserted
CREATE TRIGGER after_order_insert
AFTER INSERT ON orders
FOR EACH ROW
EXECUTE FUNCTION log_order_insert();
