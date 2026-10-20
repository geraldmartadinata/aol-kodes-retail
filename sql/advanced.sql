-- sync inventory function
CREATE OR REPLACE FUNCTION fn_trg_update_inventory()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE inventory
    SET 
        stock_level = stock_level - NEW.quantity,
        last_updated = CURRENT_TIMESTAMP
    where stock_code = NEW.stock_code;

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
