# Project Plan and Deliverables Roadmap: KoDes Retail Database Overhaul

**Client:** KoDes Retail (All-Occasion Gift Specialist)  
**Architecture:** Third Normal Form (3NF) Relational Database  
**Primary Dialects:** PostgreSQL 17+, MySQL 8.0+, SQLite  

---

## 1. Project Deliverables Checklist

- [x] Data Profiling and Imputation: Processed 1,048,575 raw rows without sampling (`data/raw/online_retail_data.xlsx`).
- [x] Phase 1 Deliverable: Entity-Relationship Diagram (ERD) normalized to 3NF (`docs/ERD.md`, `docs/erd.svg`, `docs/erd.png`).
- [x] Phase 2 Deliverable: Physical Schema DDL with PK, FK, cascades, constraints, and dynamic RFM view (`sql/schema.sql`).
- [x] Phase 3 Deliverable: Production DML business scenarios and analytical reporting queries (`sql/queries.sql`).
- [x] Phase 4 Deliverable: Real-time inventory synchronization trigger and customer history stored procedure (`sql/advanced.sql`).
- [x] Automation and Test Suite: Referential integrity verification (`scripts/verify_data.py`), query test suite (`scripts/test_queries.py`), and cloud sync CLI (`scripts/sync_supabase.py`).
- [x] Technical Documentation: Complete ETL alteration audit log (`docs/DATA_CLEANING_AND_ETL_LOG.md`) and project guide (`README.md`).

---

## 2. Phase Breakdown and Specifications

### Phase 1: Database Analysis and Architecture Design
- [x] Analyze relationships in the denormalized transactional dataset (`online_retail_data.xlsx`).
- [x] Deconstruct flat file into five normalized 3NF entities: customer, product, inventory, invoice, and invoice_line.
- [x] Formulate mathematical proof of 1NF, 2NF, and 3NF normalization.
- [x] Generate ERD with Crow's Foot notation, primary/foreign key mappings, and cardinality specifications.

### Phase 2: Physical Database Implementation (`sql/schema.sql`)
- [x] Author DDL statements (`CREATE TABLE`) for all five physical entities.
- [x] Assign storage datatypes (`INT`, `BIGINT`, `VARCHAR`, `TIMESTAMP`, `DECIMAL(10,2)`).
- [x] Enforce primary key and foreign key constraints:
  - `ON DELETE RESTRICT` for master catalog tables (customer, product) to protect against accidental orphan creation.
  - `ON DELETE CASCADE` for order line items (invoice_line) to ensure atomic order cleanup.
  - `ON UPDATE CASCADE` across all relational foreign keys.
- [x] Enforce data domain integrity: `NOT NULL`, `CHECK`, and `DEFAULT` constraints.
- [x] Create dynamic analytical view `view_customer_rfm` to eliminate transitive derivative columns from customer.
- [x] Provide high-performance bulk ingestion scripts (`\copy` for PostgreSQL, `LOAD DATA` for MySQL).

### Phase 3: Data Transactions and Analytical Queries (`sql/queries.sql`)
- [x] Scenario 1 (Price Adjustment Campaign): Update catalog `current_unit_price` by 8% for items under $5.00 using `UPDATE`.
- [x] Scenario 2 (Order Cancellation Processing): Soft-cancel orders (`status = 'Cancelled'`) without destroying transaction line items or financial audit history.
- [x] Scenario 3 (Regional Sales Breakdown): Aggregate completed sales revenue and invoice counts per country using `JOIN`, `GROUP BY`, and status filtering.
- [x] Scenario 4 (VIP High-Spender Identification): Identify registered customers whose lifetime spend strictly exceeds the global average customer spend via nested subqueries.
- [x] Scenario 5 (Cross-Border Product Performance): Query products never purchased by German customers but purchased across two or more other countries via `HAVING` and negative subquery filtering.

### Phase 4: Database Automation and Procedures (`sql/advanced.sql`)
- [x] Automated Inventory Trigger: Adjust `inventory.stock_level` on every `invoice_line` insert (decrements on sales, increments on cancellations/returns) and update `last_updated` timestamp.
- [x] Stored Procedure: Implement `GetCustomerInvoiceHistory` accepting `CustomerID` and returning complete historical orders, transaction dates, item counts, and monetary values.
- [x] Multi-RDBMS Compatibility: Provide native implementations for both PostgreSQL (`PL/pgSQL`) and MySQL 8.0+.
