-- =====================================================
-- FIX ORDERS DATA - Use actual customer IDs
-- =====================================================

-- First, let's see what customer IDs we actually have
-- Then create orders using those IDs

-- Generate orders using actual customer IDs from the database
INSERT INTO orders (order_number, customer_id, sales_rep_id, store_id, promotion_id, order_date, ship_date, delivery_date, order_status, payment_method, subtotal, tax_amount, shipping_cost, discount_amount, total_amount, profit_margin) 
SELECT 
    'ORD-2024-' || LPAD(ROW_NUMBER() OVER (ORDER BY c.customer_id)::TEXT, 6, '0') as order_number,
    c.customer_id,
    ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 55) + 1 as sales_rep_id,
    ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 35) + 1 as store_id,
    (CASE WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 4 = 0 THEN ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 10) + 1 ELSE NULL END) as promotion_id,
    CURRENT_DATE - ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 365) as order_date,
    CURRENT_DATE - ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 365) + (((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 3) + 1) as ship_date,
    CURRENT_DATE - ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 365) + (((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 3) + 4) as delivery_date,
    (CASE 
        WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 10 = 0 THEN 'Processing'
        WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 15 = 0 THEN 'Shipped'
        WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 20 = 0 THEN 'Cancelled'
        ELSE 'Completed'
    END) as order_status,
    (CASE 
        WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 3 = 0 THEN 'Credit Card'
        WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 3 = 1 THEN 'Debit Card'
        ELSE 'PayPal'
    END) as payment_method,
    (150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000))::DECIMAL(12,2) as subtotal,
    (150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000))::DECIMAL(12,2) * 0.0875 as tax_amount,
    (CASE WHEN (150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000)) > 100 THEN 0 ELSE 9.99 END)::DECIMAL(8,2) as shipping_cost,
    (CASE WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 4 = 0 THEN (150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000)) * 0.15 ELSE 0 END)::DECIMAL(10,2) as discount_amount,
    ((150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000)) * 1.0875 + (CASE WHEN (150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000)) > 100 THEN 0 ELSE 9.99 END) - (CASE WHEN ROW_NUMBER() OVER (ORDER BY c.customer_id) % 4 = 0 THEN (150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000)) * 0.15 ELSE 0 END))::DECIMAL(12,2) as total_amount,
    ((150 + ((ROW_NUMBER() OVER (ORDER BY c.customer_id) - 1) % 1000)) * 0.25)::DECIMAL(12,2) as profit_margin
FROM customers c
CROSS JOIN generate_series(1, 25) -- Generate 25 orders per customer (1000 total orders)
ORDER BY c.customer_id, generate_series;

-- Generate order items using actual order IDs and product IDs
INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost, discount_percentage, line_total, line_profit)
SELECT 
    o.order_id,
    p.product_id,
    (((o.order_id - 1) % 3) + 1) as quantity,
    p.unit_price,
    p.cost_price,
    (CASE WHEN o.order_id % 10 = 0 THEN 5.0 ELSE 0 END) as discount_percentage,
    (p.unit_price * (((o.order_id - 1) % 3) + 1)) as line_total,
    ((p.unit_price - p.cost_price) * (((o.order_id - 1) % 3) + 1)) as line_profit
FROM orders o
CROSS JOIN LATERAL (
    SELECT * FROM products 
    WHERE product_id = ((o.order_id - 1) % (SELECT COUNT(*) FROM products)) + 1
    LIMIT 1
) p;

-- Add second item for half the orders
INSERT INTO order_items (order_id, product_id, quantity, unit_price, unit_cost, discount_percentage, line_total, line_profit)
SELECT 
    o.order_id,
    p.product_id,
    1 as quantity,
    p.unit_price,
    p.cost_price,
    0 as discount_percentage,
    p.unit_price as line_total,
    (p.unit_price - p.cost_price) as line_profit
FROM orders o
CROSS JOIN LATERAL (
    SELECT * FROM products 
    WHERE product_id = ((o.order_id) % (SELECT COUNT(*) FROM products)) + 1
    LIMIT 1
) p
WHERE o.order_id % 2 = 0;

-- Update customer totals based on actual orders
UPDATE customers SET 
    total_spent = COALESCE((
        SELECT SUM(o.total_amount) 
        FROM orders o 
        WHERE o.customer_id = customers.customer_id 
        AND o.order_status = 'Completed'
    ), 0),
    last_purchase_date = (
        SELECT MAX(o.order_date) 
        FROM orders o 
        WHERE o.customer_id = customers.customer_id
    ),
    loyalty_points = COALESCE((
        SELECT SUM(o.total_amount)::INTEGER / 10 
        FROM orders o 
        WHERE o.customer_id = customers.customer_id 
        AND o.order_status = 'Completed'
    ), 0);

-- Final count
SELECT 'Orders created successfully!' as status;
SELECT COUNT(*) as total_orders FROM orders;
SELECT COUNT(*) as total_order_items FROM order_items;
SELECT SUM(total_amount) as total_revenue FROM orders WHERE order_status = 'Completed';





