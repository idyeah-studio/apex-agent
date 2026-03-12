"""
Multi-source job search using python-jobspy.
Searches LinkedIn, Indeed, Glassdoor, ZipRecruiter — no API keys needed.
"""

import time
from jobspy import scrape_jobs
from rich.console import Console
from rich.progress import track
import config

console = Console()


def search_all() -> list[dict]:
    """
    Runs searches for all role × location combinations.
    Deduplicates by URL. Returns list of raw job dicts.
    """
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    combos = [
        (role, location)
        for role in config.TARGET_ROLES
        for location in config.LOCATIONS
    ]

    console.print(f"\n[bold]🔍 Searching {len(combos)} role × location combinations across {len(config.SOURCES)} sources...[/bold]\n")

    for role, location in track(combos, description="Searching..."):
        try:
            jobs = scrape_jobs(
                site_name=config.SOURCES,
                search_term=role,
                location=location,
                results_wanted=config.RESULTS_PER_SEARCH,
                hours_old=72,                  # only jobs posted in last 3 days
                country_indeed="USA",
            )

            for _, row in jobs.iterrows():
                url = row.get("job_url", "")
                if not url or url in seen_urls:
                    continue

                company = str(row.get("company", "") or "")
                if company in config.BLOCKLIST:
                    continue

                seen_urls.add(url)
                all_jobs.append(_normalize(row, role))

            # Be polite to the sources
            time.sleep(2)

        except Exception as e:
            console.print(f"[yellow]  ⚠ Search failed for '{role}' in '{location}': {e}[/yellow]")
            continue

    console.print(f"\n[green]✓ Found {len(all_jobs)} unique jobs[/green]\n")
    return all_jobs


def _normalize(row, search_role: str) -> dict:
    """Convert a jobspy DataFrame row into a clean dict."""
    salary_min = None
    salary_max = None

    # jobspy returns min/max salary columns
    try:
        if row.get("min_amount"):
            salary_min = int(float(row["min_amount"]))
        if row.get("max_amount"):
            salary_max = int(float(row["max_amount"]))
    except (ValueError, TypeError):
        pass

    return {
        "title":       str(row.get("title", "") or ""),
        "company":     str(row.get("company", "") or ""),
        "location":    str(row.get("location", "") or ""),
        "source":      str(row.get("site", "") or ""),
        "url":         str(row.get("job_url", "") or ""),
        "description": str(row.get("description", "") or ""),
        "salary_min":  salary_min,
        "salary_max":  salary_max,
        "search_role": search_role,   # what we searched for (not stored in DB)
    }
