#!/usr/bin/env python3
"""
Apex Agent — entry point

Usage:
  python3 run.py search --profile <profile-uuid>
  python3 run.py email  --profile <profile-uuid>
  python3 server.py   # starts web UI + API (preferred)
"""

import sys
from dotenv import load_dotenv
load_dotenv()


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "search"

    # Parse --profile flag
    profile_id = None
    if "--profile" in args:
        idx = args.index("--profile")
        if idx + 1 < len(args):
            profile_id = args[idx + 1]

    if not profile_id:
        print("Error: --profile <profile-uuid> is required.")
        print("Usage: python3 run.py search --profile <uuid>")
        print("\nCreate a profile via the web dashboard at http://localhost:5050/")
        sys.exit(1)

    if cmd == "search":
        from src.agent import run
        run(profile_id)

    elif cmd == "email":
        from src.email_agent import poll_gmail_for_recruiter_emails
        from src.database import insert_email_thread
        from rich.console import Console
        console = Console()
        console.print("[bold]Polling Gmail for recruiter emails...[/bold]")
        threads = poll_gmail_for_recruiter_emails()
        for thread in threads:
            insert_email_thread(profile_id, thread)
        console.print(f"[green]✓ {len(threads)} email threads saved.[/green]")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python3 run.py [search|email] --profile <uuid>")


if __name__ == "__main__":
    main()
