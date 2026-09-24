-- =============================================================================
-- KoDes Retail Database Overhaul (Phase 2: DDL Implementation)
-- Author: Gerald Martadinata
-- Standard: Third Normal Form (3NF) Relational Architecture
-- Target Dialect: PostgreSQL / MySQL 8.0+
-- File: schema.sql
-- =============================================================================

-- =============================================================================
-- SECTION 1: TEARDOWN (CLEAN STATE)
-- Drops existing tables in reverse dependency order to prevent FK violations.
-- =============================================================================
DROP VIEW IF EXISTS view_customer_rfm CASCADE;
DROP TABLE IF EXISTS invoice_line CASCADE;
DROP TABLE IF EXISTS invoice CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS product CASCADE;
DROP TABLE IF EXISTS customer CASCADE;

-- =============================================================================
-- SECTION 2: PHYSICAL TABLE DEFINITIONS
-- =============================================================================

-- 1. CUSTOMER ENTITY
-- Stores unique customer master records.
-- 3NF Justification: Omits derived lifetime spend / dates (handled via SQL View).
-- Primary residence is assigned based on majority purchase location.
CREATE TABLE customer (
    customer_id     INT             NOT NULL,
    customer_type   VARCHAR(20)     NOT NULL,
    country         VARCHAR(60)     NOT NULL,
    CONSTRAINT pk_customer PRIMARY KEY (customer_id),
    CONSTRAINT chk_customer_type CHECK (customer_type IN ('Registered', 'Guest'))
);

-- 2. PRODUCT ENTITY
-- Catalog containing normalized descriptions and current reference prices.
-- 3NF Justification: Separates live catalog pricing from historical transaction unit prices.
CREATE TABLE product (
    stock_code          VARCHAR(30)     NOT NULL,
    description         VARCHAR(255)    NOT NULL,
    current_unit_price  DECIMAL(10, 2)  NOT NULL DEFAULT 0.00,
    CONSTRAINT pk_product PRIMARY KEY (stock_code),
    CONSTRAINT chk_product_price CHECK (current_unit_price >= 0.00)
);

-- 3. INVENTORY ENTITY
-- Physical stock tracker (1:1 with PRODUCT) to support warehouse automation.
CREATE TABLE inventory (
    stock_code      VARCHAR(30)     NOT NULL,
    stock_level     INT             NOT NULL DEFAULT 1000,
    last_updated    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_inventory PRIMARY KEY (stock_code),
    CONSTRAINT fk_inventory_product FOREIGN KEY (stock_code)
        REFERENCES product (stock_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 4. INVOICE ENTITY (ORDER MASTER)
-- Master order transaction header with unified timestamp and order lifecycle status.
-- 'country' captures destination / transaction country directly on the invoice.
CREATE TABLE invoice (
    invoice_no      VARCHAR(20)     NOT NULL,
    invoice_date    TIMESTAMP       NOT NULL,
    customer_id     INT             NOT NULL,
    country         VARCHAR(60)     NOT NULL,
    status          VARCHAR(20)     NOT NULL,
    CONSTRAINT pk_invoice PRIMARY KEY (invoice_no),
    CONSTRAINT fk_invoice_customer FOREIGN KEY (customer_id)
        REFERENCES customer (customer_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_invoice_status CHECK (status IN ('Completed', 'Cancelled', 'Loss'))
);

-- 5. INVOICE_LINE ENTITY (TRANSACTION DETAILS)
-- Atomic line items preserving actual billed unit price at the time of purchase.
CREATE TABLE invoice_line (
    line_id             BIGINT          NOT NULL,
    invoice_no          VARCHAR(20)     NOT NULL,
    stock_code          VARCHAR(30)     NOT NULL,
    quantity            INT             NOT NULL,
    unit_price_at_sale  DECIMAL(10, 2)  NOT NULL DEFAULT 0.00,
    CONSTRAINT pk_invoice_line PRIMARY KEY (line_id),
    CONSTRAINT fk_line_invoice FOREIGN KEY (invoice_no)
        REFERENCES invoice (invoice_no)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_line_product FOREIGN KEY (stock_code)
        REFERENCES product (stock_code)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_unit_price_at_sale CHECK (unit_price_at_sale >= 0.00)
);

-- =============================================================================
-- SECTION 3: PERFORMANCE INDEXES
-- Indexing high-frequency foreign keys, status filters, and join targets.
-- =============================================================================
CREATE INDEX idx_invoice_customer ON invoice (customer_id);
CREATE INDEX idx_invoice_country ON invoice (country);
CREATE INDEX idx_invoice_status ON invoice (status);
CREATE INDEX idx_invoice_date ON invoice (invoice_date);

CREATE INDEX idx_line_invoice ON invoice_line (invoice_no);
CREATE INDEX idx_line_product ON invoice_line (stock_code);

-- =============================================================================
-- SECTION 4: 3NF DERIVED VIEW (CUSTOMER ANALYTICS & RFM)
-- Computes customer first/last purchase dates and total spend on-demand,
-- preventing 3NF redundancy anomalies in the base CUSTOMER table.
-- =============================================================================
CREATE OR REPLACE VIEW view_customer_rfm AS
SELECT 
    c.customer_id,
    c.customer_type,
    c.country,
    MIN(i.invoice_date)                                 AS first_purchase_date,
    MAX(i.invoice_date)                                 AS last_purchase_date,
    COUNT(DISTINCT i.invoice_no)                        AS total_completed_invoices,
    COALESCE(SUM(l.quantity * l.unit_price_at_sale), 0) AS total_lifetime_spend
FROM customer c
LEFT JOIN invoice i 
    ON c.customer_id = i.customer_id 
   AND i.status = 'Completed'
LEFT JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
GROUP BY 
    c.customer_id, 
    c.customer_type, 
    c.country;

-- =============================================================================
-- SECTION 5: BULK INGESTION COMMANDS (FOR REFERENCE)
-- =============================================================================
/*
-- POSTGRESQL (psql CLI):
\copy customer(customer_id, customer_type, country) FROM 'data/processed/customers.csv' WITH (FORMAT csv, HEADER true);
\copy product(stock_code, description, current_unit_price) FROM 'data/processed/products.csv' WITH (FORMAT csv, HEADER true);
\copy inventory(stock_code, stock_level, last_updated) FROM 'data/processed/inventory.csv' WITH (FORMAT csv, HEADER true);
\copy invoice(invoice_no, invoice_date, customer_id, country, status) FROM 'data/processed/invoices.csv' WITH (FORMAT csv, HEADER true);
\copy invoice_line(line_id, invoice_no, stock_code, quantity, unit_price_at_sale) FROM 'data/processed/invoice_lines.csv' WITH (FORMAT csv, HEADER true);

-- MYSQL 8.0+:
LOAD DATA LOCAL INFILE 'data/processed/customers.csv' INTO TABLE customer FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
LOAD DATA LOCAL INFILE 'data/processed/products.csv' INTO TABLE product FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
LOAD DATA LOCAL INFILE 'data/processed/inventory.csv' INTO TABLE inventory FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
LOAD DATA LOCAL INFILE 'data/processed/invoices.csv' INTO TABLE invoice FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
LOAD DATA LOCAL INFILE 'data/processed/invoice_lines.csv' INTO TABLE invoice_line FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
*/
