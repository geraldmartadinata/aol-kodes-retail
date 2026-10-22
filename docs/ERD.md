# KoDes Retail Relational Architecture and Entity Relationship Diagram

This document outlines the relational architecture designed for KoDes Retail, transforming unnormalized transactional flat-file records into a normalized relational database.

The design eliminates update, insertion, and deletion anomalies, enforces referential integrity across all entities, and separates live catalog metadata from immutable transaction line items.

---

## 1. Relational Entity Relationship Diagram

```mermaid
erDiagram
    CUSTOMER ||--|{ INVOICE : places
    INVOICE ||--|{ INVOICE_LINE : contains
    PRODUCT ||--o{ INVOICE_LINE : "appears on"
    PRODUCT ||--|| INVENTORY : "stock tracked in"

    CUSTOMER {
        VARCHAR(10) customer_id PK "Unique customer alphanumeric code"
        VARCHAR(100) customer_name "Customer full name"
        VARCHAR(150) email UK "Unique customer contact email"
        VARCHAR(30) phone_number "Customer contact phone"
        VARCHAR(200) address "Customer street address"
        VARCHAR(100) city "Customer city of residence"
        VARCHAR(20) customer_type "'Registered' | 'Guest'"
        VARCHAR(60) country "Primary residence country"
    }

    INVOICE {
        VARCHAR(20) invoice_no PK "Unique order identifier"
        TIMESTAMP invoice_date "Canonical order timestamp"
        VARCHAR(10) customer_id FK "References customer(customer_id)"
        VARCHAR(60) country "Order destination country"
        VARCHAR(20) status "'Completed' | 'Cancelled' | 'Loss'"
        VARCHAR(20) payment_method "Payment method instrument"
    }

    PRODUCT {
        VARCHAR(30) stock_code PK "Unique SKU code"
        VARCHAR(255) description "Standard product description"
        VARCHAR(50) category "Product merchandise category"
        DECIMAL(10_2) current_unit_price "Current catalog price"
    }

    INVENTORY {
        VARCHAR(30) stock_code PK "Stock keeping unit identifier"
        INT stock_level "Available warehouse stock units"
        INT reorder_level "Threshold triggering inventory reorder"
        TIMESTAMP last_updated "Timestamp of last stock adjustment"
    }

    INVOICE_LINE {
        CHAR(8) line_id PK "Surrogate line item identifier"
        VARCHAR(20) invoice_no FK "References invoice(invoice_no)"
        VARCHAR(30) stock_code FK "References product(stock_code)"
        INT quantity "Billed quantity units"
        DECIMAL(10_2) unit_price_at_sale "Billed unit price at the time of purchase"
    }
```

---

## 2. Cardinalities and Relationships

| Relationship | Cardinality | Parent Table | Child Table | Foreign Key | Modality |
|:---|:---:|:---|:---|:---|:---|
| places | 1 : N | customer | invoice | customer_id | Mandatory One to Mandatory Many (`||` to `\|{`) |
| contains | 1 : N | invoice | invoice_line | invoice_no | Mandatory One to Mandatory Many (`||` to `\|{`) |
| appears on | 1 : N | product | invoice_line | stock_code | Mandatory One to Optional Many (`||` to `o{`) |
| stock tracked in | 1 : 1 | product | inventory | stock_code | Mandatory One to Mandatory One (`||` to `||`) |

---

## 3. Data Dictionary

### Table: customer
Master directory storing individual registered customers and guest checkouts.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| customer_id | VARCHAR(10) | PRIMARY KEY | Unique customer identifier. |
| customer_name | VARCHAR(100) | NOT NULL | Customer full legal/display name. |
| email | VARCHAR(150) | NOT NULL, UNIQUE | Unique account email address. |
| phone_number | VARCHAR(30) | NULL | Customer contact telephone number. |
| address | VARCHAR(200) | NOT NULL | Customer delivery address street line. |
| city | VARCHAR(100) | NOT NULL | Customer domicile city. |
| customer_type | VARCHAR(20) | NOT NULL | Membership category ('Registered' or 'Guest'). |
| country | VARCHAR(60) | NOT NULL | Customer primary country of residence. |

### Table: invoice
Order header capturing transaction-level metadata and lifecycle states.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| invoice_no | VARCHAR(20) | PRIMARY KEY | Unique order alphanumeric identifier. Orders with prefix 'C' represent cancellations. |
| invoice_date | TIMESTAMP | NOT NULL | Canonical invoice timestamp. |
| customer_id | VARCHAR(10) | NOT NULL, FK REFERENCES customer(customer_id) | Account that placed the order. |
| country | VARCHAR(60) | NOT NULL | Transaction shipping destination country. |
| status | VARCHAR(20) | NOT NULL | Order lifecycle status ('Completed', 'Cancelled', 'Loss'). |
| payment_method | VARCHAR(20) | NOT NULL | Payment instrument ('Credit Card', 'PayPal', 'Bank Transfer', etc.). |

### Table: product
Catalog master table storing active merchandise details.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| stock_code | VARCHAR(30) | PRIMARY KEY | Stock keeping unit (SKU) identifying the merchandise item. |
| description | VARCHAR(255) | NOT NULL | Canonical catalog product description. |
| category | VARCHAR(50) | NOT NULL | Merchandise department or grouping. |
| current_unit_price | DECIMAL(10,2) | NOT NULL, DEFAULT 0.00 | Current list price of the product. |

### Table: inventory
Warehouse stock ledger maintaining real-time quantity on hand.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| stock_code | VARCHAR(30) | PRIMARY KEY | Stock keeping unit identifier. |
| stock_level | INT | NOT NULL, DEFAULT 1000 | Current quantity available in the warehouse. |
| reorder_level | INT | NOT NULL, DEFAULT 100 | Minimum stock threshold before replenishment order is triggered. |
| last_updated | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Timestamp recording the most recent inventory modification. |

### Table: invoice_line
Atomic transaction items capturing historical sales.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| line_id | CHAR(8) | PRIMARY KEY | Fixed 8-character surrogate identifier for each transaction line item. |
| invoice_no | VARCHAR(20) | NOT NULL, FK REFERENCES invoice(invoice_no) | Reference to parent invoice header. |
| stock_code | VARCHAR(30) | NOT NULL, FK REFERENCES product(stock_code) | Reference to catalog product purchased. |
| quantity | INT | NOT NULL | Units purchased (positive values for sales, negative for adjustments). |
| unit_price_at_sale | DECIMAL(10,2) | NOT NULL, DEFAULT 0.00 | Actual unit price billed at the time of sale. |
