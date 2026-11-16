-- Run after the schema revision that moves stock_level and last_updated into product.
CREATE OR REPLACE FUNCTION fn_trg_update_inventory()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE product p
    SET stock_level = p.stock_level - sales.quantity,
        last_updated = CURRENT_TIMESTAMP
    FROM (
        SELECT l.stock_code, SUM(l.quantity) AS quantity
        FROM inserted_lines l
        JOIN invoice i ON i.invoice_no = l.invoice_no
        WHERE i.status = 'Completed'
        GROUP BY l.stock_code
    ) sales
    WHERE p.stock_code = sales.stock_code;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_inventory ON invoice_line;

CREATE TRIGGER trg_update_inventory
AFTER INSERT ON invoice_line
REFERENCING NEW TABLE AS inserted_lines
FOR EACH STATEMENT
EXECUTE FUNCTION fn_trg_update_inventory();

CREATE OR REPLACE FUNCTION GetCustomerInvoiceHistory(p_customer_id VARCHAR(10))
RETURNS TABLE (
    invoice_no          VARCHAR(20),
    invoice_date        TIMESTAMP,
    status              VARCHAR(20),
    country             VARCHAR(60),
    total_line_items    BIGINT,
    total_invoice_value NUMERIC(12, 2)
) LANGUAGE sql STABLE AS $$
    SELECT
        i.invoice_no,
        i.invoice_date,
        i.status,
        i.country,
        COUNT(l.invoice_no) AS total_line_items,
        ROUND(COALESCE(SUM(l.quantity * l.unit_price_at_sale), 0), 2) AS total_invoice_value
    FROM invoice i
    LEFT JOIN invoice_line l 
        ON i.invoice_no = l.invoice_no
    WHERE i.customer_id = p_customer_id
    GROUP BY i.invoice_no
    ORDER BY i.invoice_date DESC;
$$;

CREATE OR REPLACE FUNCTION fn_trg_restore_inventory_on_cancel()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE product p
    SET stock_level = p.stock_level + cancelled.quantity,
        last_updated = CURRENT_TIMESTAMP
    FROM (
        SELECT l.stock_code, SUM(l.quantity) AS quantity
        FROM updated_invoices u
        -- Cancellation keeps the invoice number fixed.
        JOIN previous_invoices b ON b.invoice_no = u.invoice_no
        JOIN invoice_line l ON l.invoice_no = u.invoice_no
        WHERE b.status = 'Completed' AND u.status = 'Cancelled'
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
