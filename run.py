#!/usr/bin/env python3
"""
Apex Agent — entry point

Usage:
  python run.py search      # search + score + draft (default)
  python run.py email       # poll Gmail + draft replies
  python run.py schedule    # run search daily at 7am
"""

import sys
from dotenv import load_dotenv
load_dotenv()

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "search"

    if cmd == "search":
        from src.agent import run
        run()

    elif cmd == "email":
        from src.email_agent import poll_gmail_for_recruiter_emails
        from src.database import insert_email_thread
        from rich.console import Console
        console = Console()
        console.print("[bold]Polling Gmail for recruiter emails...[/bold]")
        threads = poll_gmail_for_recruiter_emails()
        for thread in threads:
            insert_email_thread(thread)
        console.print(f"[green]✓ {len(threads)} email threads saved for review.[/green]")

    elif cmd == "schedule":
        import schedule
        import time
        from rich.console import Console
        from src.agent import run
        console = Console()
        schedule.every().day.at("07:00").do(run)
        console.print("[bold]Scheduler running. Searches daily at 7am. Ctrl+C to stop.[/bold]")
        while True:
            schedule.run_pending()
            time.sleep(60)

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python run.py [search|email|schedule]")


if __name__ == "__main__":
    main()
