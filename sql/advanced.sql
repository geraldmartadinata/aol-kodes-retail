-- =============================================================================
-- KoDes Retail Database Overhaul (Phase 4: Advanced Features & Automation)
-- Author: Gerald Martadinata
-- File: advanced.sql
-- =============================================================================

-- =============================================================================
-- SECTION 1: TRIGGER - AUTOMATED INVENTORY SYNCHRONIZATION
-- Requirement:
-- Create a trigger that automatically updates the inventory level of a product
-- whenever a transaction (sale or return) involving that product is recorded.
-- 
-- Business Logic:
-- • Sale (NEW.quantity > 0): Decrements stock_level by quantity.
-- • Return/Refund (NEW.quantity < 0): Increments stock_level by |quantity|.
--   Formula: stock_level = stock_level - NEW.quantity (handles both directions).
-- • Updates 'last_updated' timestamp to CURRENT_TIMESTAMP.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1A. POSTGRESQL IMPLEMENTATION
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_update_inventory()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE inventory
    SET 
        stock_level = stock_level - NEW.quantity,
        last_updated = CURRENT_TIMESTAMP
    WHERE stock_code = NEW.stock_code;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_inventory ON invoice_line;

CREATE TRIGGER trg_update_inventory
AFTER INSERT ON invoice_line
FOR EACH ROW
EXECUTE FUNCTION fn_trg_update_inventory();

-- -----------------------------------------------------------------------------
-- 1B. MYSQL 8.0+ IMPLEMENTATION
-- -----------------------------------------------------------------------------
/*
DELIMITER $$

DROP TRIGGER IF EXISTS trg_update_inventory$$

CREATE TRIGGER trg_update_inventory
AFTER INSERT ON invoice_line
FOR EACH ROW
BEGIN
    UPDATE inventory
    SET 
        stock_level = stock_level - NEW.quantity,
        last_updated = CURRENT_TIMESTAMP
    WHERE stock_code = NEW.stock_code;
END$$

DELIMITER ;
*/

-- =============================================================================
-- SECTION 2: STORED PROCEDURE - GetCustomerInvoiceHistory
-- Requirement:
-- Create a stored procedure named GetCustomerInvoiceHistory that accepts a 
-- CustomerID as input and returns a complete list of all invoices (including 
-- the date and total value) belonging to that customer.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 2A. POSTGRESQL IMPLEMENTATION (TABLE-RETURNING FUNCTION & PROCEDURE)
-- -----------------------------------------------------------------------------
-- In PostgreSQL, returning result sets to a query caller is conventionally
-- performed via a set-returning FUNCTION:
CREATE OR REPLACE FUNCTION GetCustomerInvoiceHistory(p_customer_id INT)
RETURNS TABLE (
    invoice_no          VARCHAR(20),
    invoice_date        TIMESTAMP,
    status              VARCHAR(20),
    country             VARCHAR(60),
    total_line_items    BIGINT,
    total_invoice_value NUMERIC(12, 2)
) AS $$
BEGIN
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
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- 2B. MYSQL 8.0+ IMPLEMENTATION
-- -----------------------------------------------------------------------------
/*
DELIMITER $$

DROP PROCEDURE IF EXISTS GetCustomerInvoiceHistory$$

CREATE PROCEDURE GetCustomerInvoiceHistory(IN p_customer_id INT)
BEGIN
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
END$$

DELIMITER ;
*/

-- =============================================================================
-- SECTION 3: VERIFICATION EXAMPLES
-- =============================================================================
-- Test Stored Procedure in PostgreSQL:
-- SELECT * FROM GetCustomerInvoiceHistory(12346);

-- Test Stored Procedure in MySQL:
-- CALL GetCustomerInvoiceHistory(12346);

-- Test Trigger Execution:
-- 1. Check stock before insertion:
-- SELECT * FROM inventory WHERE stock_code = '85123A';
-- 2. Insert test sale line:
-- INSERT INTO invoice_line (line_id, invoice_no, stock_code, quantity, unit_price_at_sale)
-- VALUES (999999999, '536365', '85123A', 5, 2.55);
-- 3. Verify stock decreased by 5:
-- SELECT * FROM inventory WHERE stock_code = '85123A';
