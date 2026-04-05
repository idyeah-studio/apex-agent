"""
All Supabase read/write operations for Apex Agent.
Every query is scoped to a profile_id.
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


# ── Profiles ─────────────────────────────────────────

def get_profile(profile_id: str) -> Optional[dict]:
    db = get_client()
    result = db.table("profiles").select("*").eq("id", profile_id).execute()
    return result.data[0] if result.data else None


# ── Jobs ─────────────────────────────────────────────

def job_exists(profile_id: str, url: str) -> bool:
    """Check if a job URL is already in the database for this profile."""
    db = get_client()
    result = (
        db.table("jobs")
        .select("id")
        .eq("profile_id", profile_id)
        .eq("url", url)
        .execute()
    )
    return len(result.data) > 0


def insert_job(profile_id: str, job: dict) -> Optional[str]:
    """Insert a new job scoped to a profile. Returns the job's UUID or None."""
    db = get_client()
    job["profile_id"] = profile_id
    result = db.table("jobs").insert(job).execute()
    if result.data:
        return result.data[0]["id"]
    return None


def insert_draft(profile_id: str, draft: dict) -> None:
    db = get_client()
    draft["profile_id"] = profile_id
    db.table("drafts").insert(draft).execute()


def get_all_jobs(profile_id: str) -> list[dict]:
    db = get_client()
    result = (
        db.table("jobs")
        .select("*, drafts(*)")
        .eq("profile_id", profile_id)
        .order("found_at", desc=True)
        .execute()
    )
    return result.data or []


def update_job_status(job_id: str, status: str) -> None:
    db = get_client()
    db.table("jobs").update({"status": status}).eq("id", job_id).execute()


# ── Drafts ───────────────────────────────────────────

def approve_draft(draft_id: str) -> None:
    db = get_client()
    db.table("drafts").update({"approved": True}).eq("id", draft_id).execute()


def update_draft(draft_id: str, fields: dict) -> None:
    db = get_client()
    db.table("drafts").update({**fields, "edited": True}).eq("id", draft_id).execute()


# ── Email threads ────────────────────────────────────

def insert_email_thread(profile_id: str, thread: dict) -> None:
    db = get_client()
    thread["profile_id"] = profile_id
    db.table("email_threads").insert(thread).execute()


def get_pending_email_replies(profile_id: str) -> list[dict]:
    db = get_client()
    result = (
        db.table("email_threads")
        .select("*")
        .eq("profile_id", profile_id)
        .eq("reply_approved", False)
        .is_("replied_at", "null")
        .order("received_at", desc=True)
        .execute()
    )
    return result.data or []
