-- Keep product stock synchronized for multi-row inserts.
-- A sale or write-off decreases stock; a cancellation credit increases it.
CREATE OR REPLACE FUNCTION fn_trg_update_inventory()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE product p
    SET stock_level = p.stock_level + movements.quantity,
        last_updated = CURRENT_TIMESTAMP
    FROM (
        SELECT l.stock_code,
               SUM(CASE
                       WHEN i.status = 'Cancelled' THEN l.quantity
                       WHEN i.status IN ('Completed', 'Loss') THEN -l.quantity
                       ELSE 0
                   END) AS quantity
        FROM inserted_lines l
        JOIN invoice i ON i.invoice_no = l.invoice_no
        GROUP BY l.stock_code
    ) movements
    WHERE p.stock_code = movements.stock_code
      AND movements.quantity <> 0;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_inventory ON invoice_line;

CREATE TRIGGER trg_update_inventory
AFTER INSERT ON invoice_line
REFERENCING NEW TABLE AS inserted_lines
FOR EACH STATEMENT
EXECUTE FUNCTION fn_trg_update_inventory();

-- Return one row per invoice, including invoices with no detail rows.
CREATE OR REPLACE FUNCTION GetCustomerInvoiceHistory(p_customer_id VARCHAR(10))
RETURNS TABLE (
    invoice_no          VARCHAR(20),
    invoice_date        TIMESTAMP,
    status              VARCHAR(20),
    country             VARCHAR(60),
    total_line_items    BIGINT,
    total_invoice_value NUMERIC(12, 2)
) LANGUAGE sql STABLE AS $$
    SELECT i.invoice_no,
           i.invoice_date,
           i.status,
           i.country,
           COUNT(l.invoice_no) AS total_line_items,
           ROUND(COALESCE(SUM(l.quantity * l.unit_price_at_sale), 0), 2) AS total_invoice_value
    FROM invoice i
    LEFT JOIN invoice_line l ON l.invoice_no = i.invoice_no
    WHERE i.customer_id = p_customer_id
    GROUP BY i.invoice_no, i.invoice_date, i.status, i.country
    ORDER BY i.invoice_date DESC;
$$;

-- Restore stock only when a previously completed invoice is cancelled.
CREATE OR REPLACE FUNCTION fn_trg_restore_inventory_on_cancel()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE product p
    SET stock_level = p.stock_level + cancelled.quantity,
        last_updated = CURRENT_TIMESTAMP
    FROM (
        SELECT l.stock_code, SUM(l.quantity) AS quantity
        FROM previous_invoices old_i
        JOIN updated_invoices new_i ON new_i.invoice_no = old_i.invoice_no
        JOIN invoice_line l ON l.invoice_no = new_i.invoice_no
        WHERE old_i.status = 'Completed'
          AND new_i.status = 'Cancelled'
        GROUP BY l.stock_code
    ) cancelled
    WHERE p.stock_code = cancelled.stock_code;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_restore_inventory_on_cancel ON invoice;

CREATE TRIGGER trg_restore_inventory_on_cancel
AFTER UPDATE ON invoice
REFERENCING OLD TABLE AS previous_invoices NEW TABLE AS updated_invoices
FOR EACH STATEMENT
EXECUTE FUNCTION fn_trg_restore_inventory_on_cancel();

-- Demo, run manually after import. The supplied unit price is the amount charged,
-- including any discount; it is not copied from product.current_unit_price.
-- SELECT stock_code, stock_level FROM product WHERE stock_code = '85123A';
-- INSERT INTO invoice VALUES ('DEMO-1', CURRENT_TIMESTAMP, '0', 'United Kingdom', 'Completed', 'Cash');
-- INSERT INTO invoice_line VALUES ('DEMO-1', '85123A', 10, 2.50);
-- SELECT stock_code, stock_level FROM product WHERE stock_code = '85123A';
-- SELECT * FROM GetCustomerInvoiceHistory('12346');
