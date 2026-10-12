# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
# ]
# ///

import sys
import sqlite3
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Enforce UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(highlight=False)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "retail.db"

def run_interactive():
    if not DB_PATH.exists():
        console.print(f"[bold red]Database not found at {DB_PATH}![/bold red]")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    console.print(Panel(
        f"[bold white]Connected to Local Database:[/bold white] [cyan]{DB_PATH}[/cyan]\n"
        "[dim]Type your SQL query and press Enter. Type 'exit' or 'quit' to close.[/dim]\n"
        "[dim]Tables: customer, product, inventory, invoice, invoice_line | View: view_customer_rfm[/dim]",
        title="[bold green]KoDes Retail - Local SQL Console[/bold green]",
        box=box.ROUNDED
    ))

    while True:
        try:
            query = console.input("\n[bold cyan]SQL>[/bold cyan] ").strip()
            if not query:
                continue
            if query.lower() in ['exit', 'quit', 'q']:
                console.print("[green]Goodbye![/green]")
                break

            cur.execute(query)
            if query.lower().startswith("select"):
                rows = cur.fetchall()
                col_names = [d[0] for d in cur.description] if cur.description else []
                
                if not rows:
                    console.print("[yellow]0 rows returned.[/yellow]")
                    continue

                table = Table(box=box.ROUNDED, show_lines=False)
                for col in col_names:
                    table.add_column(col, style="cyan")

                # Show max 50 rows in console
                for row in rows[:50]:
                    table.add_row(*[str(val) for val in row])

                console.print(table)
                if len(rows) > 50:
                    console.print(f"[dim]Showing first 50 of {len(rows):,} total rows.[/dim]")
            else:
                conn.commit()
                console.print(f"[green]Query executed successfully. Rows affected: {cur.rowcount}[/green]")
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]SQL Error:[/bold red] {e}")

    conn.close()

if __name__ == "__main__":
    run_interactive()
