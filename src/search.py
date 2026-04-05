"""
Apex Agent — Job Search
Source: LinkedIn public job search only.
"""

import time
import random
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import track

import config

console = Console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def search_all() -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    combos = [
        (role, location)
        for role in config.TARGET_ROLES
        for location in config.LOCATIONS
    ]

    console.print(f"\n[bold]🔍 Searching LinkedIn — {len(combos)} role × location combinations...[/bold]\n")

    for role, location in track(combos, description="Searching LinkedIn..."):
        try:
            jobs = _search_linkedin(role, location)
            added = 0
            for job in jobs:
                url = job.get("url", "")
                if not url or url in seen_urls:
                    continue
                if job.get("company", "") in config.BLOCKLIST:
                    continue
                seen_urls.add(url)
                all_jobs.append(job)
                added += 1
            if added:
                console.print(f"  [dim]LinkedIn: {added} jobs for '{role}' / '{location}'[/dim]")
        except Exception as e:
            console.print(f"[yellow]  ⚠ LinkedIn error for '{role}' / '{location}': {e}[/yellow]")

        # Respectful delay — LinkedIn rate limits aggressively
        time.sleep(random.uniform(3.0, 6.0))

    console.print(f"\n[green]✓ Found {len(all_jobs)} unique jobs[/green]\n")
    return all_jobs


def _search_linkedin(role: str, location: str) -> list[dict]:
    params = {
        "keywords": role,
        "location": location,
        "f_TPR":    "r259200",  # posted in last 3 days
        "f_E":      "4,5,6",    # mid-senior, director, executive
        "start":    "0",
    }
    url = "https://www.linkedin.com/jobs/search/?" + urlencode(params)

    resp = SESSION.get(url, timeout=20)

    if resp.status_code == 429:
        wait = random.randint(30, 60)
        console.print(f"[yellow]  ⚠ LinkedIn rate limited — waiting {wait}s[/yellow]")
        time.sleep(wait)
        resp = SESSION.get(url, timeout=20)

    if resp.status_code != 200:
        console.print(f"[yellow]  ⚠ LinkedIn returned {resp.status_code} for '{role}' / '{location}'[/yellow]")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    cards = soup.select("div.base-card, li.jobs-search__results-list > div")

    for card in cards[:config.RESULTS_PER_SEARCH]:
        title_el   = card.select_one("h3.base-search-card__title, h3.job-search-card__title")
        company_el = card.select_one("h4.base-search-card__subtitle, a.job-search-card__subtitle-link")
        loc_el     = card.select_one("span.job-search-card__location")
        link_el    = card.select_one("a.base-card__full-link, a.job-search-card__title-link")

        title   = title_el.get_text(strip=True)  if title_el   else ""
        company = company_el.get_text(strip=True) if company_el else ""
        loc     = loc_el.get_text(strip=True)     if loc_el     else location
        link    = link_el.get("href", "")         if link_el    else ""

        if not title or not link:
            continue

        link = link.split("?")[0]  # strip tracking params

        jobs.append({
            "title":       title,
            "company":     company,
            "location":    loc,
            "source":      "linkedin",
            "url":         link,
            "description": "",
            "salary_min":  None,
            "salary_max":  None,
        })

    return jobs