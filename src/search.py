"""
Apex Agent — Job Search
Source: LinkedIn public job search only.
"""

import time
import random
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from rich.console import Console

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

RESULTS_PER_SEARCH = 50

# US state abbreviations → full names for matching
US_STATES = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas",
    "ca": "california", "co": "colorado", "ct": "connecticut", "de": "delaware",
    "fl": "florida", "ga": "georgia", "hi": "hawaii", "id": "idaho",
    "il": "illinois", "in": "indiana", "ia": "iowa", "ks": "kansas",
    "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota", "ms": "mississippi",
    "mo": "missouri", "mt": "montana", "ne": "nebraska", "nv": "nevada",
    "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico", "ny": "new york",
    "nc": "north carolina", "nd": "north dakota", "oh": "ohio", "ok": "oklahoma",
    "or": "oregon", "pa": "pennsylvania", "ri": "rhode island", "sc": "south carolina",
    "sd": "south dakota", "tn": "tennessee", "tx": "texas", "ut": "utah",
    "vt": "vermont", "va": "virginia", "wa": "washington", "wv": "west virginia",
    "wi": "wisconsin", "wy": "wyoming",
}


def _build_location_filter(locations: list[str]) -> callable:
    """Build a function that checks if a job location matches preferred locations."""
    allowed_terms = set()
    has_remote = False

    for loc in locations:
        loc_lower = loc.lower().strip()

        if "remote" in loc_lower:
            has_remote = True
            continue

        # Split "San Francisco, CA" → ["san francisco", "ca"]
        parts = [p.strip() for p in loc_lower.split(",")]
        for p in parts:
            allowed_terms.add(p)
            # Expand state abbreviations: "ca" → also allow "california"
            if p in US_STATES:
                allowed_terms.add(US_STATES[p])

    def matches(job_location: str) -> bool:
        if not job_location:
            return False
        loc = job_location.lower()

        # "Remote" jobs always match if Remote is in preferences
        if has_remote and "remote" in loc:
            return True

        # Check if any preferred term appears in the job location
        return any(term in loc for term in allowed_terms)

    return matches


def search_streaming(
    target_roles: list[str],
    locations: list[str],
    blocklist: list[str] | None = None,
    li_at: str | None = None,
):
    """
    Generator that yields (role, location, matched_jobs) per search combo.
    Jobs are location-filtered before yielding.
    """
    blocklist = blocklist or []
    seen_urls: set[str] = set()
    location_ok = _build_location_filter(locations)

    if li_at:
        SESSION.cookies.set("li_at", li_at, domain=".linkedin.com")

    combos = [
        (role, location)
        for role in target_roles
        for location in locations
    ]

    console.print(f"\n[bold]Searching LinkedIn — {len(combos)} combinations...[/bold]\n")

    for role, location in combos:
        try:
            raw_jobs = _search_linkedin(role, location)
        except Exception as e:
            console.print(f"[yellow]  Error for '{role}' / '{location}': {e}[/yellow]")
            time.sleep(random.uniform(3.0, 6.0))
            continue

        matched = []
        for job in raw_jobs:
            url = job.get("url", "")
            if not url or url in seen_urls:
                continue
            if job.get("company", "") in blocklist:
                continue
            if not location_ok(job.get("location", "")):
                continue
            seen_urls.add(url)
            matched.append(job)

        yield role, location, matched
        time.sleep(random.uniform(3.0, 6.0))

    console.print(f"\n[green]Search complete.[/green]\n")


def _search_linkedin(role: str, location: str) -> list[dict]:
    params = {
        "keywords": role,
        "location": location,
        "f_TPR":    "r259200",
        "f_E":      "4,5,6",
        "start":    "0",
    }
    url = "https://www.linkedin.com/jobs/search/?" + urlencode(params)

    resp = SESSION.get(url, timeout=20)

    if resp.status_code == 429:
        wait = random.randint(30, 60)
        console.print(f"[yellow]  Rate limited — waiting {wait}s[/yellow]")
        time.sleep(wait)
        resp = SESSION.get(url, timeout=20)

    if resp.status_code != 200:
        console.print(f"[yellow]  LinkedIn returned {resp.status_code} for '{role}' / '{location}'[/yellow]")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    cards = soup.select("div.base-card, li.jobs-search__results-list > div")

    for card in cards[:RESULTS_PER_SEARCH]:
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

        link = link.split("?")[0]

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
