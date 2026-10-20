-- preview price update
select 
    stock_code,
    description,
    current_unit_price                      as old_price,
    round(current_unit_price * 1.08, 2)     as simulated_new_price,
    round(current_unit_price * 0.08, 2)     as price_delta
from product
where current_unit_price < 5.00
order by current_unit_price desc;

-- update product prices
UPDATE product
SET current_unit_price = ROUND(current_unit_price * 1.08, 2)
WHERE current_unit_price < 5.00;

-- check order details
SELECT 
    i.invoice_no,
    i.invoice_date,
    i.customer_id,
    i.status,
    COUNT(l.line_id)                                    AS total_items,
    ROUND(SUM(l.quantity * l.unit_price_at_sale), 2)    AS order_total
FROM invoice i
JOIN invoice_line l ON i.invoice_no = l.invoice_no
WHERE i.invoice_no = '536365'
GROUP BY i.invoice_no, i.invoice_date, i.customer_id, i.status;

-- cancel order
update invoice
SET status = 'Cancelled'
WHERE invoice_no = '536365';

-- check invoice status
SELECT invoice_no, customer_id, status 
FROM invoice 
WHERE invoice_no = '536365';

-- sales by country
SELECT 
    i.country,
    COUNT(DISTINCT i.invoice_no)                        AS total_completed_invoices,
    ROUND(SUM(l.quantity * l.unit_price_at_sale), 2)    AS total_sales_revenue,
    ROUND(AVG(l.quantity * l.unit_price_at_sale), 2)    AS avg_line_value
FROM invoice i
JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
WHERE i.status = 'Completed'
GROUP BY i.country
ORDER BY total_sales_revenue DESC;

-- high spending customers
SELECT 
    c.customer_id,
    c.customer_name,
    c.email,
    c.phone,
    c.customer_type,
    c.country,
    ROUND(SUM(l.quantity * l.unit_price_at_sale), 2) AS customer_total_spend
FROM customer c
JOIN invoice i 
    ON c.customer_id = i.customer_id
JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
WHERE i.status = 'Completed'
  AND c.customer_type = 'Registered'
GROUP BY c.customer_id, c.customer_name, c.email, c.phone, c.customer_type, c.country
HAVING SUM(l.quantity * l.unit_price_at_sale) > (
    SELECT AVG(customer_spend)
    FROM (
        SELECT SUM(sub_l.quantity * sub_l.unit_price_at_sale) AS customer_spend
        FROM invoice sub_i
        JOIN invoice_line sub_l 
            ON sub_i.invoice_no = sub_l.invoice_no
        JOIN customer sub_c 
            ON sub_i.customer_id = sub_c.customer_id
        WHERE sub_i.status = 'Completed'
          AND sub_c.customer_type = 'Registered'
        GROUP BY sub_i.customer_id
    ) AS all_customers_summary
)
ORDER BY customer_total_spend DESC;

-- products outside germany
SELECT 
    p.stock_code,
    p.description,
    p.current_unit_price,
    COUNT(DISTINCT i.country)   AS purchasing_countries_count
FROM product p
JOIN invoice_line l 
    ON p.stock_code = l.stock_code
JOIN invoice i 
    ON l.invoice_no = i.invoice_no
WHERE i.status = 'Completed'
  AND p.stock_code NOT IN (
      SELECT DISTINCT sub_l.stock_code
      FROM invoice sub_i
      JOIN invoice_line sub_l 
          ON sub_i.invoice_no = sub_l.invoice_no
      WHERE sub_i.country = 'Germany'
        AND sub_i.status = 'Completed'
  )
GROUP BY 
    p.stock_code, 
    p.description, 
    p.current_unit_price
having COUNT(DISTINCT i.country) >= 2
ORDER BY 
    purchasing_countries_count DESC, 
    p.stock_code ASC;