# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
# ]
# ///

import sqlite3
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

def test_queries():
    db_path = Path("data/retail.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    console.print("\n[bold green]Testing Analytical Queries on data/retail.db...[/bold green]\n")

    # Query 3: Regional Sales Breakdown
    q3 = """
    SELECT 
        i.country,
        COUNT(DISTINCT i.invoice_no)                        AS total_completed_invoices,
        ROUND(SUM(l.quantity * l.unit_price_at_sale), 2)    AS total_sales_revenue,
        ROUND(AVG(l.quantity * l.unit_price_at_sale), 2)    AS avg_line_value
    FROM invoice i
    JOIN invoice_line l ON i.invoice_no = l.invoice_no
    WHERE i.status = 'Completed'
    GROUP BY i.country
    ORDER BY total_sales_revenue DESC
    LIMIT 5;
    """
    cur.execute(q3)
    t3 = Table(title="Query 3: Top 5 Regional Sales Breakdown (Completed Only)")
    t3.add_column("Country")
    t3.add_column("Completed Invoices", justify="right")
    t3.add_column("Total Revenue", justify="right")
    t3.add_column("Avg Line Value", justify="right")
    for r in cur.fetchall():
        t3.add_row(r[0], f"{r[1]:,}", f"${r[2]:,.2f}", f"${r[3]:,.2f}")
    console.print(t3)

    # Query 4: VIP High-Spender Identification (Filtered for Registered customers)
    q4 = """
    SELECT 
        c.customer_id,
        c.customer_name,
        c.email,
        c.phone_number,
        c.city,
        c.country,
        ROUND(SUM(l.quantity * l.unit_price_at_sale), 2) AS customer_total_spend
    FROM customer c
    JOIN invoice i ON c.customer_id = i.customer_id
    JOIN invoice_line l ON i.invoice_no = l.invoice_no
    WHERE i.status = 'Completed'
      AND c.customer_type = 'Registered'
    GROUP BY c.customer_id, c.customer_name, c.email, c.phone_number, c.city, c.country
    HAVING SUM(l.quantity * l.unit_price_at_sale) > (
        SELECT AVG(customer_spend)
        FROM (
            SELECT SUM(sub_l.quantity * sub_l.unit_price_at_sale) AS customer_spend
            FROM invoice sub_i
            JOIN invoice_line sub_l ON sub_i.invoice_no = sub_l.invoice_no
            JOIN customer sub_c ON sub_i.customer_id = sub_c.customer_id
            WHERE sub_i.status = 'Completed'
              AND sub_c.customer_type = 'Registered'
            GROUP BY sub_i.customer_id
        )
    )
    ORDER BY customer_total_spend DESC
    LIMIT 5;
    """
    cur.execute(q4)
    t4 = Table(title="Query 4: Top 5 VIP High-Spenders (Registered Only)")
    t4.add_column("Customer ID")
    t4.add_column("Name")
    t4.add_column("Email")
    t4.add_column("Phone")
    t4.add_column("City")
    t4.add_column("Country")
    t4.add_column("Total Spend", justify="right")
    for r in cur.fetchall():
        t4.add_row(str(r[0]), r[1], r[2], r[3], r[4], r[5], f"${r[6]:,.2f}")
    console.print(t4)

    # View RFM check
    q_rfm = """
    SELECT customer_id, customer_type, country, total_completed_invoices, ROUND(total_lifetime_spend, 2)
    FROM view_customer_rfm
    WHERE customer_type = 'Registered'
    ORDER BY total_lifetime_spend DESC
    LIMIT 5;
    """
    cur.execute(q_rfm)
    t_rfm = Table(title="view_customer_rfm: Top 5 Registered Customers")
    t_rfm.add_column("Customer ID")
    t_rfm.add_column("Type")
    t_rfm.add_column("Country")
    t_rfm.add_column("Invoices", justify="right")
    t_rfm.add_column("Lifetime Spend", justify="right")
    for r in cur.fetchall():
        t_rfm.add_row(str(r[0]), r[1], r[2], f"{r[3]:,}", f"${r[4]:,.2f}")
    console.print(t_rfm)

    conn.close()

if __name__ == "__main__":
    test_queries()