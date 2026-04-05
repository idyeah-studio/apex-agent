"""
All Supabase read/write operations for Apex Agent.
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def job_exists(url: str) -> bool:
    """Check if a job URL is already in the database."""
    db = get_client()
    result = db.table("jobs").select("id").eq("url", url).execute()
    return len(result.data) > 0


def insert_job(job: dict) -> Optional[str]:
    """Insert a new job. Returns the job's UUID or None on failure."""
    db = get_client()
    result = db.table("jobs").insert(job).execute()
    if result.data:
        return result.data[0]["id"]
    return None


def insert_draft(draft: dict) -> None:
    db = get_client()
    db.table("drafts").insert(draft).execute()


def get_jobs_by_status(status: str) -> list[dict]:
    db = get_client()
    result = (
        db.table("jobs")
        .select("*, drafts(*)")
        .eq("status", status)
        .order("score", desc=True)
        .execute()
    )
    return result.data or []


def get_all_jobs() -> list[dict]:
    db = get_client()
    result = (
        db.table("jobs")
        .select("*, drafts(*)")
        .order("found_at", desc=True)
        .execute()
    )
    return result.data or []


def update_job_status(job_id: str, status: str) -> None:
    db = get_client()
    db.table("jobs").update({"status": status}).eq("id", job_id).execute()


def approve_draft(draft_id: str) -> None:
    db = get_client()
    db.table("drafts").update({"approved": True}).eq("id", draft_id).execute()


def update_draft(draft_id: str, fields: dict) -> None:
    db = get_client()
    db.table("drafts").update({**fields, "edited": True}).eq("id", draft_id).execute()


def get_pipeline_stats() -> dict:
    """Return counts per status for the dashboard header."""
    db = get_client()
    result = db.table("jobs").select("status").execute()
    rows = result.data or []
    stats = {
        "new": 0, "reviewed": 0, "applied": 0,
        "interviewing": 0, "offer": 0, "rejected": 0,
    }
    for row in rows:
        s = row.get("status", "new")
        if s in stats:
            stats[s] += 1
    stats["total"] = len(rows)
    return stats


def insert_email_thread(thread: dict) -> None:
    db = get_client()
    db.table("email_threads").insert(thread).execute()


def get_pending_email_replies() -> list[dict]:
    db = get_client()
    result = (
        db.table("email_threads")
        .select("*")
        .eq("reply_approved", False)
        .is_("replied_at", "null")
        .order("received_at", desc=True)
        .execute()
    )
    return result.data or []