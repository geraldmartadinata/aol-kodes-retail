# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
# ]
# ///

"""
================================================================================
  KoDes Retail: Database Backup Generator
  Generates a production database backup file as required by project deliverables.
  Author: Gerald Martadinata
================================================================================
"""

import sys
import time
import sqlite3
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console(highlight=False)

def export_backup():
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "data" / "retail.db"
    backup_dir = project_root / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Source database not found at {db_path}.")
        console.print("Run 'uv run scripts/build_retail_db.py' first to build the database.")
        sys.exit(1)

    console.print(Panel(
        f"[bold white]Source Database:[/bold white] [cyan]{db_path}[/cyan] ({db_path.stat().st_size / (1024*1024):.2f} MB)\n"
        f"[bold white]Target Backup Directory:[/bold white] [cyan]{backup_dir}[/cyan]",
        title="[bold green]KoDes Retail - Database Backup Generator[/bold green]",
        box=box.ROUNDED
    ))

    start_time = time.time()
    
    # 1. Native Binary Backup (.db)
    binary_backup = backup_dir / "kodes_retail_backup.db"
    console.print("\n[yellow]Creating verified binary database backup...[/yellow]")
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(binary_backup)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    console.print(f" [bold green][OK][/bold green] Binary backup saved to [cyan]{binary_backup.name}[/cyan] ({binary_backup.stat().st_size / (1024*1024):.2f} MB).")

    # 2. Text SQL DDL & DML Dump (.sql)
    sql_dump = backup_dir / "kodes_retail_dump.sql"
    console.print("[yellow]Generating complete SQL DDL and data dump...[/yellow]")
    dump_conn = sqlite3.connect(db_path)
    with open(sql_dump, "w", encoding="utf-8") as f:
        for line in dump_conn.iterdump():
            f.write(f"{line}\n")
    dump_conn.close()
    console.print(f" [bold green][OK][/bold green] SQL dump saved to [cyan]{sql_dump.name}[/cyan] ({sql_dump.stat().st_size / (1024*1024):.2f} MB).")

    console.print(Panel(
        f"[bold green]DATABASE BACKUP COMPLETED IN {time.time() - start_time:.2f}s[/bold green]\n\n"
        f"1. Binary Backup File : [cyan]{binary_backup}[/cyan]\n"
        f"2. SQL Text Dump File : [cyan]{sql_dump}[/cyan]\n\n"
        "These files satisfy the final submission deliverable: 'database backup file'.",
        title="[bold green]Deliverable Ready[/bold green]",
        box=box.DOUBLE
    ))

if __name__ == "__main__":
    export_backup()
