-- sync inventory function (status-aware)
-- invoice_line.quantity is always positive; the direction comes from invoice.status:
--   Completed -> stock decreases | Cancelled (return/credit) -> stock increases | Loss (write-off) -> stock decreases
CREATE OR REPLACE FUNCTION fn_trg_update_inventory()
RETURNS TRIGGER AS $$
DECLARE
    v_status VARCHAR(20);
BEGIN
    SELECT status INTO v_status
    FROM invoice
    WHERE invoice_no = NEW.invoice_no;

    UPDATE inventory
    SET 
        stock_level  = stock_level + CASE WHEN v_status = 'Cancelled' THEN NEW.quantity ELSE -NEW.quantity END,
        last_updated = CURRENT_TIMESTAMP
    WHERE stock_code = NEW.stock_code;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- trigger on invoice line
DROP TRIGGER IF EXISTS trg_update_inventory ON invoice_line;

CREATE TRIGGER trg_update_inventory
AFTER INSERT ON invoice_line
FOR EACH ROW
EXECUTE FUNCTION fn_trg_update_inventory();

-- customer invoice history
CREATE OR REPLACE FUNCTION GetCustomerInvoiceHistory(p_customer_id INT)
RETURNS TABLE (
    invoice_no          VARCHAR(20),
    invoice_date        TIMESTAMP,
    status              VARCHAR(20),
    country             VARCHAR(60),
    total_line_items    BIGINT,
    total_invoice_value NUMERIC(12, 2)
) AS $$
begin
    RETURN QUERY
    SELECT 
        i.invoice_no,
        i.invoice_date,
        i.status,
        i.country,
        COUNT(l.line_id)                                                AS total_line_items,
        ROUND(COALESCE(SUM(l.quantity * l.unit_price_at_sale), 0), 2)  AS total_invoice_value
    FROM invoice i
    LEFT JOIN invoice_line l 
        ON i.invoice_no = l.invoice_no
    WHERE i.customer_id = p_customer_id
    GROUP BY 
        i.invoice_no, 
        i.invoice_date, 
        i.status, 
        i.country
    ORDER BY 
        i.invoice_date DESC;
end;
$$ LANGUAGE plpgsql;

-- OPTIONAL: restore stock when an existing Completed invoice is cancelled via UPDATE (Query 2)
CREATE OR REPLACE FUNCTION fn_trg_restore_inventory_on_cancel()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE inventory inv
    SET 
        stock_level  = inv.stock_level + s.qty,
        last_updated = CURRENT_TIMESTAMP
    FROM (
        SELECT stock_code, SUM(quantity) AS qty
        FROM invoice_line
        WHERE invoice_no = NEW.invoice_no
        GROUP BY stock_code
    ) s
    WHERE inv.stock_code = s.stock_code;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_restore_inventory_on_cancel ON invoice;

CREATE TRIGGER trg_restore_inventory_on_cancel
AFTER UPDATE OF status ON invoice
FOR EACH ROW
WHEN (OLD.status = 'Completed' AND NEW.status = 'Cancelled')
EXECUTE FUNCTION fn_trg_restore_inventory_on_cancel();

-- DEMO (run manually after import; uncomment): a sale lowers stock by 10
-- SELECT stock_code, stock_level FROM inventory WHERE stock_code = '85123A';
-- INSERT INTO invoice VALUES ('DEMO-1', CURRENT_TIMESTAMP, 0, 'United Kingdom', 'Completed');
-- INSERT INTO invoice_line VALUES ((SELECT MAX(line_id) + 1 FROM invoice_line), 'DEMO-1', '85123A', 10, 2.50);
-- SELECT stock_code, stock_level FROM inventory WHERE stock_code = '85123A';
-- SELECT * FROM GetCustomerInvoiceHistory(12346);