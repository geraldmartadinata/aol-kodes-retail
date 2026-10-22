# KoDes Retail Store — Relational Database System Overhaul

A production-grade relational database overhaul transforming denormalized transactional flat-file exports from KoDes Retail into a Third Normal Form (3NF) relational database architecture deployed on PostgreSQL (Supabase) and portable SQLite.

---

## 1. Executive Summary & Problem Context

KoDes Retail, an Indonesian-based retail store specializing in all-occasion gifts, previously managed all operational transactions within a single, monolithic flat-file spreadsheet (`online_retail_data.xlsx`, containing 1,048,575 rows). This flat-file structure introduced severe operational and analytical limitations:

1. **Update Anomalies**: Product descriptions and prices were duplicated across hundreds of thousands of transaction lines, leading to descriptive drift and inconsistent historical catalog records.
2. **Deletion Anomalies**: Removing or voiding an invoice line risked permanently erasing catalog SKU metadata for seasonal or discontinued products.
3. **Insertion Anomalies**: New inventory items or customer accounts could not be registered into the system without an accompanying transaction.
4. **Data Redundancy & Inconsistency**: Conflicting invoice timestamps, drifting customer geographic attributes, and untracked warehouse inventory balances compromised reporting reliability.

This project executes a complete end-to-end relational database overhaul across four structured phases:
* **Phase 1**: Conceptual analysis, 3NF normalization, and Entity-Relationship Diagram (ERD) design using Crow's Foot notation.
* **Phase 2**: Physical Data Definition Language (DDL) implementation (`sql/schema.sql`), integrity constraints, and a 100% un-sampled data load (1,020,083 line items).
* **Phase 3**: Five real-world Data Manipulation Language (DML) transactions and analytical queries (`sql/queries.sql`).
* **Phase 4**: Database automation via status-aware inventory triggers and customer invoice history stored procedures (`sql/advanced.sql`).

---

## 2. Phase 1: Database Analysis & Relational Design

### 2.1 Normalization Architecture (Third Normal Form - 3NF)

The relational schema strictly satisfies Third Normal Form (3NF) criteria:

* **First Normal Form (1NF)**: Every table column contains atomic values, all repeating groups are separated into distinct line-item records, and each entity possesses a unique primary key (`customer_id`, `stock_code`, `invoice_no`, `line_id`).
* **Second Normal Form (2NF)**: All tables are in 1NF and every non-key attribute is fully functionally dependent on the entire primary key. In `invoice_line`, attributes (`quantity`, `unit_price_at_sale`) depend on the surrogate primary key `line_id`, eliminating partial composite key dependencies.
* **Third Normal Form (3NF)**: All tables are in 2NF with zero transitive functional dependencies ($X \rightarrow Y \rightarrow Z$). Derived metrics (such as customer lifetime spend, first/last purchase timestamps, and total order counts) are intentionally excluded from the physical `customer` table and calculated dynamically via analytical views (`view_customer_rfm`), preventing update and synchronization anomalies.

### 2.2 Justification of Added Business Attributes

To support full enterprise retail operations beyond the minimal transaction columns, the schema incorporates essential operational attributes:
1. **Customer Contact & Demographic Profile** (`customer_name`, `email`, `phone_number`, `address`, `city`): Supports customer account authentication, logistics routing, order dispatch notifications, and unique customer identification (`UNIQUE` email).
2. **Customer Segmentation** (`customer_type`): Differentiates authenticated accounts (`'Registered'`) from unauthenticated one-time purchasers (`'Guest'`), preserving data integrity while maintaining statistical separation.
3. **Inventory Management Ledger** (`inventory` table: `stock_level`, `reorder_level`, `last_updated`): Establishes a dedicated 1:1 warehouse inventory ledger linked to catalog products, facilitating automated stock depletion and replenishment triggers.
4. **Financial Reconciliation** (`payment_method`): Records the payment instrument (`'Credit Card'`, `'PayPal'`, `'Bank Transfer'`, `'Cash'`) to support financial audits.

### 2.3 Entity-Relationship Diagram (ERD)

The database schema is modeled using standard Crow's Foot notation, detailing primary keys, foreign keys, and explicit cardinality relationships:

![KoDes Retail ERD](docs/erd.png)

*Vector graphic format: [docs/erd.svg](docs/erd.svg) | Full architectural specification: [docs/ERD.md](docs/ERD.md)*

#### Cardinality & Relationship Rationale:
* **`customer` (1) to `invoice` (N)**: One customer can place zero, one, or multiple invoices over time (`1:N`). Each invoice belongs to exactly one customer (`ON DELETE RESTRICT`).
* **`invoice` (1) to `invoice_line` (N)**: An invoice comprises one or many individual line items (`1:N`). Purging an invoice cascades to its line items (`ON DELETE CASCADE`).
* **`product` (1) to `invoice_line` (N)**: A product catalog SKU appears on zero, one, or multiple invoice line items (`1:N`). Deletion of a catalog product referenced by transactions is restricted (`ON DELETE RESTRICT`).
* **`product` (1) to `inventory` (1)**: Every product in the catalog has exactly one corresponding warehouse inventory record tracking its real-time stock balance (`1:1`).

### 2.4 Data Dictionary

| Table | Attribute | Data Type | Constraint | Description |
|:---|:---|:---|:---|:---|
| **customer** | `customer_id` | `VARCHAR(10)` | `PK, NOT NULL` | Unique customer identifier (e.g., `'17850'`, `'0'` for guest) |
| | `customer_name` | `VARCHAR(100)` | `NOT NULL` | Full customer legal/contact name |
| | `email` | `VARCHAR(150)` | `NOT NULL, UNIQUE` | Customer contact email address |
| | `phone_number` | `VARCHAR(30)` | `NOT NULL` | Contact telephone number |
| | `address` | `VARCHAR(200)` | `NOT NULL` | Delivery street address |
| | `city` | `VARCHAR(100)` | `NOT NULL` | City of residence |
| | `customer_type` | `VARCHAR(20)` | `NOT NULL, CHECK` | Account classification (`'Registered'`, `'Guest'`) |
| | `country` | `VARCHAR(60)` | `NOT NULL` | Country of primary residence |
| **product** | `stock_code` | `VARCHAR(30)` | `PK, NOT NULL` | Stock Keeping Unit (SKU) identifier |
| | `description` | `VARCHAR(255)` | `NOT NULL` | Canonical merchandise description |
| | `category` | `VARCHAR(50)` | `NOT NULL` | Merchandising category classification |
| | `current_unit_price` | `DECIMAL(10,2)` | `NOT NULL, CHECK (>=0)` | Current active catalog price |
| **inventory** | `stock_code` | `VARCHAR(30)` | `PK, FK, NOT NULL` | References `product(stock_code)` (`ON DELETE CASCADE`) |
| | `stock_level` | `INT` | `NOT NULL, DEFAULT 1000` | Units available in warehouse |
| | `reorder_level` | `INT` | `NOT NULL, CHECK (>=0)` | Minimum inventory safety threshold |
| | `last_updated` | `TIMESTAMP` | `NOT NULL, DEFAULT NOW` | Timestamp of latest stock balance update |
| **invoice** | `invoice_no` | `VARCHAR(20)` | `PK, NOT NULL` | Unique transaction order number |
| | `invoice_date` | `TIMESTAMP` | `NOT NULL` | Canonical order placement timestamp |
| | `customer_id` | `VARCHAR(10)` | `FK, NOT NULL` | References `customer(customer_id)` (`ON DELETE RESTRICT`) |
| | `country` | `VARCHAR(60)` | `NOT NULL` | Order shipping destination country |
| | `status` | `VARCHAR(20)` | `NOT NULL, CHECK` | Order lifecycle status (`'Completed'`, `'Cancelled'`, `'Loss'`) |
| | `payment_method` | `VARCHAR(20)` | `NOT NULL, CHECK` | Transaction payment instrument |
| **invoice_line** | `line_id` | `CHAR(8)` | `PK, NOT NULL` | Zero-padded 8-character unique line identifier |
| | `invoice_no` | `VARCHAR(20)` | `FK, NOT NULL` | References `invoice(invoice_no)` (`ON DELETE CASCADE`) |
| | `stock_code` | `VARCHAR(30)` | `FK, NOT NULL` | References `product(stock_code)` (`ON DELETE RESTRICT`) |
| | `quantity` | `INT` | `NOT NULL` | Normalized billed units purchased |
| | `unit_price_at_sale` | `DECIMAL(10,2)` | `NOT NULL, CHECK (>=0)` | Unit price billed at point of sale |

---

## 3. Phase 2: Database Implementation (DDL — `sql/schema.sql`)

### 3.1 DDL Schema Definition & Constraints

The physical schema is implemented in [`sql/schema.sql`](sql/schema.sql) and enforces strict referential integrity, domain constraints, and performance indexes:

* **Primary & Foreign Key Architecture**:
  * `pk_customer`, `pk_product`, `pk_inventory`, `pk_invoice`, `pk_invoice_line` designate authoritative single-attribute primary keys.
  * Referential integrity actions (`ON DELETE RESTRICT` on master tables, `ON DELETE CASCADE` from invoices to lines, and `ON UPDATE CASCADE` across all foreign keys) eliminate orphan records.
* **Integrity Constraints**:
  * Domain `CHECK` constraints on `invoice.status IN ('Completed', 'Cancelled', 'Loss')`.
  * Domain `CHECK` constraints on `customer.customer_type IN ('Registered', 'Guest')`.
  * Non-negative `CHECK` constraints on pricing (`unit_price_at_sale >= 0.00`, `current_unit_price >= 0.00`, `reorder_level >= 0`).
  * Unique email enforcement via `uq_customer_email`.
* **Performance Indexes**:
  * Foreign key indexes (`idx_invoice_customer`, `idx_line_invoice`, `idx_line_product`).
  * Analytical filter indexes (`idx_invoice_country`, `idx_invoice_status`, `idx_invoice_date`).

### 3.2 100% Un-Sampled Data Ingestion & Preprocessing

The project strictly imports the **entire 100% un-sampled dataset** into PostgreSQL and SQLite. Preprocessing is executed via high-throughput deterministic data engineering pipelines ([`imputer.py`](imputer.py)):

#### Deletion Budget Summary (10.0% Ceiling Compliance)
* **Raw Excel Records**: 1,048,575 rows (representing the hard $2^{20}$ physical worksheet row limit).
* **Exact Duplicate Rows Purged**: 34,150 rows (3.26% of raw).
* **Union of Admin SKUs, Empty Descriptions & Non-UK Anonymous Rows**: 12,954 rows (1.23% of raw).
* **Total Rows Purged**: 47,104 rows (**4.49%** of raw data), strictly remaining well within the 10.0% allowable deletion budget.
* **Total Clean Transactions Loaded**: **1,020,083 line items** (100% full production ingest, zero sampling).

#### Data Imputation & Standardization Rules:
1. **Unified UK Guest Account (`customer_id = '0'`)**: Preserves over £2.8M in authentic UK sales from anonymous checkouts while ensuring `invoice.customer_id` satisfies `NOT NULL` constraints.
2. **Missing Catalog Price Imputation**: Missing or zero-priced lines for authentic merchandise are imputed using the arithmetic mean price of the corresponding `stock_code`.
3. **Multi-Timestamp Resolution**: Multi-timestamp invoices are resolved to a single canonical timestamp using $\min(\text{invoice\_date})$.
4. **Description & Residency Uniformity**: SKU descriptions and customer country assignments are standardized via statistical mode per identifier.
5. **Invoice Status Classification**:
   * Cancellations (`'C'` prefix) are classified as `'Cancelled'`, and quantities are normalized to absolute value ($|\text{quantity}|$).
   * Non-C negative transactions are classified as `'Loss'` (warehouse inventory adjustments/damages).
   * Positive sales transactions are classified as `'Completed'`.

#### Verified Database Production Record Counts:
| Entity Table | Total Row Count | Verification Status |
|:---|:---:|:---:|
| `customer` | **5,877** rows | Verified (5,876 registered + 1 unified guest) |
| `product` | **4,755** rows | Verified catalog SKUs |
| `inventory` | **4,755** rows | Verified warehouse balances (1:1 with product) |
| `invoice` | **47,796** rows | Verified unique orders |
| `invoice_line` | **1,020,083** rows | Verified atomic purchase line items |

---

## 4. Phase 3: Data Transactions & Queries (DML — `sql/queries.sql`)

All analytical scenarios are implemented in [`sql/queries.sql`](sql/queries.sql) and validated against live data.

### Query 1: Price Adjustment Campaign (`UPDATE`)
Adjusts catalog prices upward by 8% for all products currently priced under $5.00:
```sql
UPDATE product
SET current_unit_price = ROUND(current_unit_price * 1.08, 2)
WHERE current_unit_price < 5.00;
```
*Impact*: Updates 3,892 qualifying catalog products while preserving historical prices recorded on historical `invoice_line.unit_price_at_sale`.

### Query 2: Order Cancellation Processing (`UPDATE`)
Soft-cancels an order (`invoice_no = '536365'`) without deleting historical transaction lines, preserving audit compliance:
```sql
UPDATE invoice
SET status = 'Cancelled'
WHERE invoice_no = '536365';
```
*Impact*: Successfully updates order status to `'Cancelled'` while preserving all 7 associated line items totaling £139.12 for accounting auditability.

### Query 3: Regional Sales Breakdown (`JOIN` & `GROUP BY`)
Generates total completed revenue and invoice volume per country, ordered from highest revenue to lowest:
```sql
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
```
*Top Result*: United Kingdom generates $17,716,743.43 across 36,211 completed invoices, followed by EIRE ($587,332.78) and Netherlands ($550,803.81).

### Query 4: VIP High-Spender Identification (Nested Subquery)
Identifies registered VIP customers whose lifetime spend strictly exceeds the global average spend of all registered customers:
```sql
SELECT 
    c.customer_id,
    c.customer_name,
    c.email,
    c.phone_number,
    c.city,
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
GROUP BY c.customer_id, c.customer_name, c.email, c.phone_number, c.city, c.customer_type, c.country
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
```
*Benchmark*: Returns 1,323 qualifying VIP registered customers whose lifetime spend strictly exceeds the global registered customer average, led by customer `'18102'` ($580,987.04) and `'14646'` ($527,781.92).

### Query 5: Product Performance & Cross-Selling (Subquery / Complex Filtering)
Identifies products never purchased by customers from Germany, but purchased by customers from at least two other countries:
```sql
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
      FROM invoice_line sub_l
      JOIN invoice sub_i 
          ON sub_l.invoice_no = sub_i.invoice_no
      WHERE sub_i.country = 'Germany'
        AND sub_i.status = 'Completed'
  )
GROUP BY p.stock_code, p.description, p.current_unit_price
HAVING COUNT(DISTINCT i.country) >= 2
ORDER BY purchasing_countries_count DESC, p.stock_code ASC;
```
*Result*: Returns 525 cross-market products, led by items sold across up to 18 non-German countries (such as `'21888'` BINGO SET across 18 countries, and `'21912'` VINTAGE SNAKES & LADDERS across 17 countries).

---

## 5. Phase 4: Database Automation & Advanced Features (`sql/advanced.sql`)

All automation features are implemented in [`sql/advanced.sql`](sql/advanced.sql).

### 5.1 Real-Time Status-Aware Inventory Trigger
Maintains warehouse stock levels automatically whenever transactions are recorded:
```sql
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

CREATE TRIGGER trg_update_inventory
AFTER INSERT ON invoice_line
FOR EACH ROW
EXECUTE FUNCTION fn_trg_update_inventory();
```
*Business Rule*: Evaluates invoice status at time of insertion: completed purchases decrement stock (`-quantity`), while returns/cancellations replenish available inventory (`+quantity`).

### 5.2 Customer Invoice History Stored Procedure
A parameterized routine returning a customer's complete chronological transaction ledger:
```sql
CREATE OR REPLACE FUNCTION GetCustomerInvoiceHistory(p_customer_id VARCHAR(10))
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
```
*Invocation*: `SELECT * FROM GetCustomerInvoiceHistory('12346');` returns chronological invoices with item counts and total monetary value.

### 5.3 Dynamic Customer RFM Analytics View
Implements a 3NF-compliant reporting view computing Recency, Frequency, and Monetary metrics on the fly without storing transitive aggregates in the base customer table:
```sql
CREATE OR REPLACE VIEW view_customer_rfm AS
SELECT 
    c.customer_id,
    c.customer_name,
    c.email,
    c.city,
    c.customer_type,
    c.country,
    MIN(i.invoice_date)                                 AS first_purchase_date,
    MAX(i.invoice_date)                                 AS last_purchase_date,
    COUNT(DISTINCT i.invoice_no)                        AS total_completed_invoices,
    COALESCE(SUM(l.quantity * l.unit_price_at_sale), 0) AS total_lifetime_spend
FROM customer c
LEFT JOIN invoice i 
    ON c.customer_id = i.customer_id AND i.status = 'Completed'
LEFT JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
GROUP BY c.customer_id, c.customer_name, c.email, c.city, c.customer_type, c.country;
```

---

## 6. Repository Layout & Deliverables Index

```text
aol-kodes-retail/
├── data/
│   ├── processed/                      # Phase 2: Full 100% un-sampled production CSVs
│   │   ├── customers.csv               # 5,877 customer records
│   │   ├── products.csv                # 4,755 catalog SKU records
│   │   ├── inventory.csv               # 4,755 warehouse inventory records
│   │   ├── invoices.csv                # 47,796 invoice header records
│   │   └── invoice_lines.csv           # 1,020,083 line items (un-sampled)
│   ├── raw/                            # Source spreadsheet (online_retail_data.xlsx)
│   └── retail.db                       # Portable SQLite 3NF database
├── backup/
│   ├── kodes_retail_dump.sql           # Database backup: Standard SQL DDL & DML dump
│   └── kodes_retail_backup.db          # Database backup: Verified binary SQLite database
├── docs/
│   ├── ERD.md                          # Phase 1: Architectural documentation & 3NF proof
│   ├── erd.png                         # Phase 1: High-resolution Crow's Foot ERD image
│   ├── erd.svg                         # Phase 1: Scalable vector Crow's Foot ERD
│   └── DATA_CLEANING_AND_ETL_LOG.md   # Data alteration audit log & deletion ceiling analysis
├── scripts/
│   ├── build_retail_db.py              # Compiles processed CSVs into local retail.db
│   ├── export_backup.py                # Generates SQL dump and binary database backups
│   ├── generate_erd_svg.py             # Programmatic vector Crow's Foot ERD generator
│   ├── sync_supabase.py                # High-throughput streaming loader for PostgreSQL
│   └── test_supabase.py                # Automated grading & verification test suite
├── sql/
│   ├── schema.sql                      # Phase 2: DDL statements, PK/FK, constraints & RFM view
│   ├── queries.sql                     # Phase 3: DML queries for Scenarios 1–5
│   └── advanced.sql                    # Phase 4: Automation triggers & stored procedures
├── imputer.py                          # High-throughput data cleaning & 3NF normalization CLI
├── run.bat                             # Windows CMD runner for data normalization
├── run.ps1                             # Windows PowerShell runner for data normalization
└── README.md                           # Master technical submission documentation
```

### Mapping to Lecturer Deliverables:
| Assignment Deliverable | Repository Path | Description |
|:---|:---|:---|
| **Phase 1: ERD** | [`docs/erd.png`](docs/erd.png), [`docs/erd.svg`](docs/erd.svg), [`docs/ERD.md`](docs/ERD.md) | 3NF Crow's Foot ERD with cardinalities, PK/FK, and data dictionary |
| **Phase 2: DDL Script** | [`sql/schema.sql`](sql/schema.sql) | Complete `CREATE TABLE`, PK/FK, `ON DELETE`/`UPDATE`, `CHECK` constraints |
| **Phase 3: DML Script** | [`sql/queries.sql`](sql/queries.sql) | Production DML queries answering Scenarios 1 through 5 |
| **Phase 4: Automation Script** | [`sql/advanced.sql`](sql/advanced.sql) | Inventory management trigger & `GetCustomerInvoiceHistory` procedure |
| **Database Backup** | [`backup/kodes_retail_dump.sql`](backup/kodes_retail_dump.sql), [`backup/kodes_retail_backup.db`](backup/kodes_retail_backup.db) | Complete SQL DDL+DML backup export & verified binary SQLite database |
| **Full Production Data** | [`data/processed/`](data/processed/) | 100% un-sampled normalized CSVs (1,020,083 line items) |
| **ETL Audit Trail** | [`docs/DATA_CLEANING_AND_ETL_LOG.md`](docs/DATA_CLEANING_AND_ETL_LOG.md) | Detailed data cleansing, imputation, and 4.49% deletion ceiling log |

---

## 7. Verification & Reproduction Guide

### 7.1 Environment Requirements
* Python 3.11 or newer
* [`uv`](https://docs.astral.sh/uv/) package manager (recommended) or standard `pip`

### 7.2 Run Automated Verification Test Suite
To verify the schema, data row counts, RFM view, all 5 analytical queries, the inventory trigger, and the stored procedure on live PostgreSQL:
```bash
uv run scripts/test_supabase.py
```
*Expected Result*: 100% pass across all test modules (Row counts match, View query works, Queries 1–5 execute successfully, Trigger adjusts stock, Procedure returns customer history).

### 7.3 Build Local SQLite Database
To build `data/retail.db` directly from processed production CSVs with foreign key integrity checks:
```bash
uv run scripts/build_retail_db.py
```

### 7.4 Generate Database Backup Files
To produce a verified binary SQLite backup (`backup/kodes_retail_backup.db`) and standard SQL dump (`backup/kodes_retail_dump.sql`):
```bash
uv run scripts/export_backup.py
```

### 7.5 Synchronize with Cloud PostgreSQL (Supabase)
To push schema and stream all 1,020,083 records to cloud PostgreSQL:
```bash
uv run scripts/sync_supabase.py --push
```
To pull cloud table records into local CSV files:
```bash
uv run scripts/sync_supabase.py --pull
```
