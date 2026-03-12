"""
Email agent — monitors Gmail for recruiter threads and drafts replies.

Uses the Gmail MCP (already connected in Claude) OR the Gmail API directly.
For standalone use: set up Google Cloud project → OAuth credentials →
download as gmail_credentials.json.
"""

import os
import anthropic
import config

_client = anthropic.Anthropic()


CLASSIFY_PROMPT = """
You are parsing a recruiter email received by a senior design leader job seeker.

Email subject: {subject}
From: {sender}
Body:
{body}

Classify the intent of this email. Respond with ONLY one of these strings:
interview_request
rejection
info_request
offer
follow_up
other

Then on the next line, write a one-sentence summary of what they want.
"""


REPLY_PROMPT = """
You are a ghostwriter for a senior UX design leader. Draft a reply to this recruiter email.

## Candidate voice
{voice}

## Email received
Subject: {subject}
From: {sender}
Intent: {intent}
Body:
{body}

## Instructions
- 2–4 sentences. Direct, warm but not eager.
- If interview_request: accept gracefully, offer a couple of time windows.
- If info_request: answer concisely, offer to send more if needed.
- If rejection: reply with class, keep the door open.
- If offer: express interest, ask for details / offer letter.
- Never start with "Hope you're doing well" or "Thank you for reaching out."
- Sign off as: Vishal

Write only the reply body. No subject line.
"""


def classify_email(subject: str, sender: str, body: str) -> dict:
    """Returns {"intent": str, "summary": str}"""
    prompt = CLASSIFY_PROMPT.format(
        subject=subject, sender=sender, body=body[:2000]
    )
    try:
        response = _client.messages.create(
            model="claude-haiku-4-5-20251001",   # fast + cheap for classification
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        lines = response.content[0].text.strip().splitlines()
        intent = lines[0].strip() if lines else "other"
        summary = lines[1].strip() if len(lines) > 1 else ""
        return {"intent": intent, "summary": summary}
    except Exception as e:
        return {"intent": "other", "summary": f"Classification error: {e}"}


def draft_reply(subject: str, sender: str, body: str, intent: str) -> str:
    """Draft a reply for the recruiter email."""
    prompt = REPLY_PROMPT.format(
        voice=config.VOICE,
        subject=subject,
        sender=sender,
        intent=intent,
        body=body[:2000],
    )
    try:
        response = _client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"[Reply draft failed: {e}]"


# ── Gmail polling (via Google API) ────────────────────

def poll_gmail_for_recruiter_emails():
    """
    Polls Gmail for unread emails that look like recruiter/HR threads.
    Requires gmail_credentials.json (OAuth2).

    This function is a scaffold — wire it to your Gmail OAuth setup
    or use the Gmail MCP in the Claude dashboard directly.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        import base64

        SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "./gmail_credentials.json")

        # Auth
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        service = build("gmail", "v1", credentials=creds)

        # Search for recruiter-like emails
        query = "is:unread (subject:opportunity OR subject:role OR subject:position OR subject:interview) -from:me"
        results = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
        messages = results.get("messages", [])

        threads = []
        for msg in messages:
            detail = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            subject = headers.get("Subject", "")
            sender = headers.get("From", "")
            body_data = detail["payload"].get("body", {}).get("data", "")
            if not body_data and detail["payload"].get("parts"):
                body_data = detail["payload"]["parts"][0].get("body", {}).get("data", "")
            body = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="ignore") if body_data else ""

            classification = classify_email(subject, sender, body)
            reply = draft_reply(subject, sender, body, classification["intent"])

            threads.append({
                "gmail_thread_id": detail.get("threadId", ""),
                "sender_name":     sender.split("<")[0].strip(),
                "sender_email":    sender,
                "subject":         subject,
                "last_message":    body[:1000],
                "intent":          classification["intent"],
                "draft_reply":     reply,
            })

        return threads

    except ImportError:
        print("Gmail API not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        return []
    except Exception as e:
        print(f"Gmail polling error: {e}")
        return []
