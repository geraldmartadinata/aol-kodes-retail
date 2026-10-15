# Project Specification: Relational Database for KoDes Retail Store

- **Client:** KoDes Retail (All-Occasion Gift Specialist, Indonesia)
- **Project:** Relational Database Implementation
- **Due Date:** Any time before UAS
- **Final Deliverables:** Three `.sql` files (`schema.sql`, `queries.sql`, `advanced.sql`), documentation explaining the work, and a database backup file.

---

## 1. Project Background & Core Objective

### 1.1 The Scenario
KoDes Retail is an Indonesian-based retail store specializing in all-occasion gifts. For the past several years, they have managed their business by exporting all transaction data into a single, large CSV file.

This flat-file approach has reached its limit. The client is experiencing significant operational friction:
- Generating reports is slow.
- Data is frequently inconsistent.
- Making simple updates (like changing a product's name) is a monumental task.

The mission is to replace this outdated spreadsheet system with a professionally designed, secure, and efficient relational database.

### 1.2 The Core Objective
Take the client's raw transaction data and use it as a blueprint to design, implement, and test a fully normalized relational database system from scratch. This new system must:
- Ensure ACID data integrity.
- Eliminate redundancy.
- Handle complex business queries efficiently.

### 1.3 The Source Data
All available historical data is provided in a single flat file with the following columns:
- `Invoice`: Transaction / invoice identifier
- `StockCode`: Product SKU code
- `Description`: Product name / description
- `Quantity`: Number of units purchased or returned
- `InvoiceDate`: Transaction date and timestamp
- `Price`: Unit price per item
- `Customer ID`: Customer identifier
- `Country`: Customer or transaction country

---

## 2. Project Deliverables Overview

| Deliverable | Target File | Description |
|:---|:---|:---|
| **Phase 1: Database Design** | `docs/ERD.md` (or diagram) | Entity-Relationship Diagram (ERD) normalized to at least 3NF |
| **Phase 2: DDL Implementation** | `sql/schema.sql` | Table definitions, datatypes, PK/FK, cascades, and constraints |
| **Phase 3: DML Queries** | `sql/queries.sql` | 5 analytical and transactional business query scenarios |
| **Phase 4: Automation** | `sql/advanced.sql` | Automated trigger for inventory and customer history stored procedure |
| **Documentation** | `README.md`, `docs/` | Technical explanation of design, normalization, and ETL process |
| **Database Backup** | `backup/` | Verified database backup / dump file |

---

## 3. Strict Project Constraints

1. **Strictly No Data Sampling:**
   - Preprocessing using another programming language is allowed.
   - Using only a sample of the data as the final import is **strictly prohibited**. The full dataset must be imported into the database.
2. **Normalized to At Least 3NF:**
   - The database design must eliminate all partial and transitive functional dependencies.
3. **Non-Destructive Order Cancellation:**
   - Order cancellation (Query 2) must update the invoice status to `'Cancelled'` without deleting historical audit records or transaction line items.
4. **Enforced Referential Integrity:**
   - Primary Keys (PK) and Foreign Keys (FK) must be clearly designated.
   - Referential integrity actions (`ON DELETE`, `ON UPDATE`) must be explicitly declared.
   - Other constraints (`NOT NULL`, `CHECK`, `DEFAULT`, `UNIQUE`) must be utilized to maintain data quality.

---

## 4. Phase-by-Phase Requirements & Things to Do

### Phase 1: Database Analysis & Design
- [ ] Analyze the source flat-file data and identify core business concepts (e.g., sales, products, customers).
- [ ] Design a normalized relational schema that separates concepts into related tables.
- [ ] Add justified new attributes or tables where appropriate (e.g., tracking inventory levels).
- [ ] Ensure the schema is normalized to at least Third Normal Form (3NF).
- [ ] Create an Entity-Relationship Diagram (ERD) clearly visualizing all tables and their attributes.
- [ ] Mark each table's Primary Key (PK) and all Foreign Keys (FK) using standard Crow's Foot notation.

### Phase 2: Database Implementation (DDL)
- [ ] Create a single SQL script named `schema.sql`.
- [ ] Include all `CREATE TABLE` statements for the normalized schema.
- [ ] Select appropriate data types for every column.
- [ ] Define all Primary Key and Foreign Key constraints.
- [ ] Define referential integrity actions (`ON DELETE`, `ON UPDATE`).
- [ ] Implement data quality constraints (`NOT NULL`, `CHECK`, `DEFAULT`, `UNIQUE`).
- [ ] Import complete data from CSV into the database without sampling.

### Phase 3: Data Transactions & Queries (DML)
- [ ] Create a single SQL script named `queries.sql`.
- [ ] **Query 1: Price Adjustment Campaign (UPDATE)**  
  Due to inflation and exchange rates, increase `UnitPrice` by 8% for all products that currently cost less than $5.00.
- [ ] **Query 2: Order Cancellation Processing (UPDATE/DELETE)**  
  Customer requests to cancel an order (`InvoiceNo`). Update the status of that invoice to `'Cancelled'` without deleting historical audit records.
- [ ] **Query 3: Regional Sales Breakdown (JOIN & GROUP BY)**  
  Generate a report showing total sales revenue and total completed invoices per `Country`, ordered from highest revenue to lowest.
- [ ] **Query 4: VIP High-Spender Identification (Nested Query / Subquery Required)**  
  Find all customers whose total spend is greater than the average total spend of all customers in the database. Output customer details along with calculated total spend.
- [ ] **Query 5: Product Performance & Cross-Selling (Subquery / Complex Filtering)**  
  Identify products that have never been purchased by any customer from `'Germany'`, but have been purchased by customers from at least two other countries.

### Phase 4: Advanced Features & Automation
- [ ] Create a single SQL script named `advanced.sql`.
- [ ] **Trigger:**  
  Create a database trigger that automatically updates the inventory level of a product whenever a transaction (sale or return) involving that product is recorded.
- [ ] **Stored Procedure:**  
  Create a stored procedure named `GetCustomerInvoiceHistory` that accepts a `CustomerID` as input and returns a complete list of all invoices (including the date and total value) belonging to that customer.
