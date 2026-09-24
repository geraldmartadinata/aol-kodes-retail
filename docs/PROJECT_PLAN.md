# Project Plan & Deliverables Roadmap: KoDes Retail Database Overhaul

**Client:** KoDes Retail (All-Occasion Gift Specialist)  
**Deliverables Checklist:**
- [x] Preprocessing & Imputation of raw data (1,048,575 rows without sampling)
- [x] **Phase 1 Deliverable:** Entity-Relationship Diagram (ERD) normalized to 3NF (`docs/ERD.md`)
- [x] **Phase 2 Deliverable:** `schema.sql` (Physical DDL, Datatypes, PK/FK, Cascades, Constraints, RFM View, Bulk Import)
- [x] **Phase 3 Deliverable:** `queries.sql` (5 required DML business scenarios & complex analytics)
- [x] **Phase 4 Deliverable:** `advanced.sql` (Inventory adjustment trigger & Customer invoice history stored procedure)
- [ ] Final Documentation & Database Backup Dump

---

## Phase Breakdown & Requirements

### Phase 1: Database Analysis & Design (Completed)
- [x] Investigate relationships in flat-file (`online_retail_data.xlsx`).
- [x] Deconstruct into core entities: `customers`, `products`, `invoices`, `invoice_items`, `inventory`.
- [x] Normalize to Third Normal Form (3NF).
- [x] Generate ERD with Crow's Foot notation and Foreign Keys.

### Phase 2: Database Implementation (`schema.sql`)
- [ ] Write DDL statements (`CREATE TABLE`) for all 5 entities.
- [ ] Assign precise datatypes (`INT`, `BIGINT`, `VARCHAR`, `TIMESTAMP`, `DECIMAL(10,2)`).
- [ ] Enforce Primary Key and Foreign Key constraints.
- [ ] Define referential integrity actions:
  - `ON DELETE RESTRICT` for master tables (`customers`, `products`).
  - `ON DELETE CASCADE` for dependent line items (`invoice_items`).
  - `ON UPDATE CASCADE` across all foreign keys.
- [ ] Define data quality constraints: `NOT NULL`, `CHECK`, `DEFAULT`.
- [ ] Provide bulk import script (`COPY` / `LOAD DATA`) to load all 1M+ rows.

### Phase 3: Data Transactions & Queries (`queries.sql`)
- [ ] **Query 1: Price Adjustment Campaign (UPDATE)**  
  Increase `UnitPrice` by 8% for all products costing less than $5.00 due to inflation/exchange rates.
- [ ] **Query 2: Order Cancellation Processing (UPDATE/DELETE)**  
  Update an order status to `'Cancelled'` for a requested `InvoiceNo` without deleting audit history.
- [ ] **Query 3: Regional Sales Breakdown (JOIN & GROUP BY)**  
  Generate a report showing total revenue and total completed invoices per `Country`, sorted highest to lowest.
- [ ] **Query 4: VIP High-Spender Identification (Nested Subquery)**  
  Find all customers whose total spend exceeds the average total spend of all customers in the database.
- [ ] **Query 5: Product Performance & Cross-Selling (Subquery / Complex Filtering)**  
  Identify products never purchased by any customer from `'Germany'`, but purchased by customers from at least two other countries.

### Phase 4: Advanced Features & Automation (`advanced.sql`)
- [ ] **Trigger:** Automatically adjust `inventory.stock_level` whenever a transaction is recorded (decrements on positive sale, increments on negative return/cancellation).
- [ ] **Stored Procedure:** `GetCustomerInvoiceHistory(CustomerID)` accepting a `CustomerID` input and returning all invoices (including date and total order value).
