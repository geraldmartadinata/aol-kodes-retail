-- =============================================================================
-- KoDes Retail Database Overhaul (Phase 3: DML Transactions & Analytical Queries)
-- Author: Gerald Martadinata
-- File: queries.sql
-- =============================================================================

-- =============================================================================
-- SCENARIO 1: Price Adjustment Campaign (UPDATE)
-- Business Context:
-- Due to inflation and exchange rate fluctuations, KoDes Retail needs to increase
-- the catalog UnitPrice by 8% for all products that currently cost less than $5.00.
-- =============================================================================

-- 1A. Verification Query (Inspect products affected prior to update)
SELECT 
    stock_code,
    description,
    current_unit_price                      AS old_price,
    ROUND(current_unit_price * 1.08, 2)     AS simulated_new_price,
    ROUND(current_unit_price * 0.08, 2)     AS price_delta
FROM product
WHERE current_unit_price < 5.00
ORDER BY current_unit_price DESC;

-- 1B. Production DML Execution
UPDATE product
SET current_unit_price = ROUND(current_unit_price * 1.08, 2)
WHERE current_unit_price < 5.00;

-- =============================================================================
-- SCENARIO 2: Order Cancellation Processing (UPDATE/DELETE)
-- Business Context:
-- A customer requests to cancel an order (e.g., InvoiceNo = '536365').
-- Update the status of that invoice to 'Cancelled' without deleting historical
-- audit records (preserving line items for financial audit and stock reconciliation).
-- =============================================================================

-- 2A. Inspect invoice status and associated line items before update
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

-- 2B. Production DML Execution (Soft Cancellation maintaining Audit Trail)
UPDATE invoice
SET status = 'Cancelled'
WHERE invoice_no = '536365';

-- 2C. Confirm state change
SELECT invoice_no, customer_id, status 
FROM invoice 
WHERE invoice_no = '536365';

-- =============================================================================
-- SCENARIO 3: Regional Sales Breakdown (JOIN & GROUP BY)
-- Business Context:
-- Generate a comprehensive performance report showing total sales revenue and
-- total completed invoices per Country. Order from highest revenue to lowest.
-- Note: Must strictly filter for completed orders (excluding cancellations & losses).
-- =============================================================================
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

-- =============================================================================
-- SCENARIO 4: VIP High-Spender Identification (Nested Query / Subquery Required)
-- Business Context:
-- Identify high-value customers whose calculated total spend is strictly greater
-- than the average total spend of all customers in the database.
-- Output customer details along with their calculated total spend.
-- =============================================================================

-- Approach: Subquery calculates the global average customer spend,
-- while the outer query filters and ranks qualifying VIP customers.
SELECT 
    c.customer_id,
    c.customer_type,
    c.country,
    ROUND(SUM(l.quantity * l.unit_price_at_sale), 2) AS customer_total_spend
FROM customer c
JOIN invoice i 
    ON c.customer_id = i.customer_id
JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
WHERE i.status = 'Completed'
GROUP BY c.customer_id, c.customer_type, c.country
HAVING SUM(l.quantity * l.unit_price_at_sale) > (
    -- Subquery: Average total spend across all purchasing customers
    SELECT AVG(customer_spend)
    FROM (
        SELECT SUM(sub_l.quantity * sub_l.unit_price_at_sale) AS customer_spend
        FROM invoice sub_i
        JOIN invoice_line sub_l 
            ON sub_i.invoice_no = sub_l.invoice_no
        WHERE sub_i.status = 'Completed'
        GROUP BY sub_i.customer_id
    ) AS all_customers_summary
)
ORDER BY customer_total_spend DESC;

-- =============================================================================
-- SCENARIO 5: Product Performance & Cross-Selling (Subquery / Complex Filtering)
-- Business Context:
-- Identify products that have NEVER been purchased by any customer from 'Germany',
-- but HAVE been purchased by customers from at least two other countries.
-- =============================================================================
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
      -- Subquery: Products ordered by customers situated in Germany
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
HAVING COUNT(DISTINCT i.country) >= 2
ORDER BY 
    purchasing_countries_count DESC, 
    p.stock_code ASC;
