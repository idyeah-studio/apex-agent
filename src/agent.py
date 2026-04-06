"""
Apex Agent — main loop.

Jobs are saved to the database as they're found (not batched at the end),
so partial results are available if the agent is stopped mid-run.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from src import search, database

console = Console()


def run(profile_id: str):
    """Search for jobs and save each one immediately."""
    profile = database.get_profile(profile_id)
    if not profile:
        console.print(f"[red]Profile {profile_id} not found.[/red]")
        return

    console.rule("[bold gold1]APEX AGENT[/bold gold1]")
    console.print(f"[dim]Profile: {profile['name']}[/dim]\n")

    target_roles = profile.get("target_roles") or []
    locations = profile.get("locations") or []
    blocklist = profile.get("blocklist") or []

    if not target_roles or not locations:
        console.print("[yellow]No target roles or locations configured. Update your profile settings.[/yellow]")
        return

    saved = 0
    seen_urls = set()

    # Search each combo and save jobs immediately
    for role, location, jobs in search.search_streaming(
        target_roles=target_roles,
        locations=locations,
        blocklist=blocklist,
        li_at=profile.get("linkedin_li_at"),
    ):
        for job in jobs:
            url = job.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            # Deduplicate against DB
            if database.job_exists(profile_id, url):
                continue

            try:
                db_job = {
                    "title":       job["title"],
                    "company":     job["company"],
                    "location":    job["location"],
                    "source":      job["source"],
                    "url":         url,
                    "description": (job.get("description") or "")[:10000],
                    "salary_min":  job.get("salary_min"),
                    "salary_max":  job.get("salary_max"),
                    "status":      "new",
                }
                job_id = database.insert_job(profile_id, db_job)
                if job_id:
                    saved += 1
            except Exception as e:
                console.print(f"[red]Error saving {job.get('title')}: {e}[/red]")

        console.print(f"  [dim]{len(jobs)} found for '{role}' / '{location}' — {saved} total saved[/dim]")

    console.print(f"\n[bold green]✓ {saved} jobs saved. Open the dashboard to review and score.[/bold green]\n")
