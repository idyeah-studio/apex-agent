"""
Apex Agent — main loop.

Flow:
  search → deduplicate → score → filter → draft → save to Supabase
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table
from rich.progress import track

import config
from src import search, scorer, drafter, database

console = Console()


def run():
    console.rule("[bold gold1]APEX AGENT[/bold gold1]")
    console.print()

    # ── 1. Search ──────────────────────────────────────
    raw_jobs = search.search_all()

    if not raw_jobs:
        console.print("[yellow]No jobs found. Check your config or try later.[/yellow]")
        return

    # ── 2. Deduplicate against DB ──────────────────────
    new_jobs = []
    for job in raw_jobs:
        if job.get("url") and database.job_exists(job["url"]):
            continue
        new_jobs.append(job)

    console.print(f"[cyan]{len(new_jobs)} new jobs (not seen before)[/cyan]\n")

    if not new_jobs:
        console.print("[green]Nothing new today. Already tracking everything.[/green]")
        return

    # ── 3. Score + filter ──────────────────────────────
    scored = []
    console.print("[bold]Scoring jobs with Claude...[/bold]")
    for job in track(new_jobs, description="Scoring..."):
        result = scorer.score_job(job)
        job.update(result)

        # Apply dream company bonus
        if job.get("company") in config.DREAM_COMPANIES:
            job["score"] = min(100, job["score"] + 10)

        if job["score"] >= config.SCORE_THRESHOLD:
            scored.append(job)

    console.print(f"\n[green]{len(scored)} jobs above threshold ({config.SCORE_THRESHOLD})[/green]")

    # ── 4. Preview scored jobs ─────────────────────────
    _print_table(scored)

    # ── 5. Draft + save ────────────────────────────────
    saved = 0
    console.print("\n[bold]Drafting applications...[/bold]")
    for job in track(scored, description="Drafting..."):
        try:
            # Save job first
            db_job = {
                "title":           job["title"],
                "company":         job["company"],
                "location":        job["location"],
                "source":          job["source"],
                "url":             job["url"],
                "description":     (job.get("description") or "")[:10000],
                "salary_min":      job.get("salary_min"),
                "salary_max":      job.get("salary_max"),
                "score":           job["score"],
                "score_reasoning": job.get("score_reasoning", ""),
                "status":          "new",
            }
            job_id = database.insert_job(db_job)
            if not job_id:
                continue

            # Generate drafts
            drafts = drafter.draft_all(job)
            drafts["job_id"] = job_id
            database.insert_draft(drafts)
            saved += 1

        except Exception as e:
            console.print(f"[red]Error saving {job.get('title')} @ {job.get('company')}: {e}[/red]")

    console.print(f"\n[bold green]✓ {saved} jobs saved with drafts. Open the dashboard to review.[/bold green]\n")


def _print_table(jobs: list[dict]) -> None:
    table = Table(title="Top Matches", show_header=True, header_style="bold gold1")
    table.add_column("Score", width=6, justify="center")
    table.add_column("Title", width=30)
    table.add_column("Company", width=22)
    table.add_column("Location", width=20)
    table.add_column("Source", width=12)

    sorted_jobs = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)
    for j in sorted_jobs[:20]:
        score = j.get("score", 0)
        color = "green" if score >= 80 else "yellow" if score >= 65 else "white"
        table.add_row(
            f"[{color}]{score}[/{color}]",
            j.get("title", "")[:30],
            j.get("company", "")[:22],
            j.get("location", "")[:20],
            j.get("source", ""),
        )

    console.print(table)


if __name__ == "__main__":
    run()
