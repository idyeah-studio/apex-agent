"""
Claude drafts tailored cover letters, application emails,
and LinkedIn connection notes for each approved job.
"""

import anthropic

_client = anthropic.Anthropic()


COVER_LETTER_PROMPT = """
You are a ghostwriter for a job candidate. Write a cover letter for this job application.

## Candidate voice and style
{voice}

## Candidate background
{resume}

## The job
Title: {title}
Company: {company}
Location: {location}

Job description:
{description}

## Instructions
- 3 paragraphs maximum. Each paragraph is 2–3 sentences.
- Paragraph 1: Concrete hook — why this specific company/role now. Reference something real about them.
- Paragraph 2: The single most relevant thing about the candidate for this role. One story or proof point.
- Paragraph 3: Forward-looking close. No "I look forward to hearing from you." Something more specific.
- Do NOT start with "I am writing to apply for..."
- Do NOT use bullet points
- Sign off as: {signoff}

Write only the letter body. No subject line. No metadata.
"""


EMAIL_PROMPT = """
You are a ghostwriter for a job candidate. Write a short outreach email to apply for a role.

## Candidate voice and style
{voice}

## Candidate background (brief)
{resume_brief}

## The job
Title: {title}
Company: {company}

## Instructions
- Subject line: concise, specific, not generic
- Body: 3–4 sentences total. Why them, who the candidate is, one sentence ask.
- No bullets. No "I hope this email finds you well."
- Sign off as: {signoff}

Respond with:
SUBJECT: <subject line>
BODY:
<email body>
"""


LINKEDIN_NOTE_PROMPT = """
Write a LinkedIn connection request note for someone applying to this role.

Role: {title} at {company}
Candidate: {name}, {summary}
Voice: {voice}

Rules:
- 300 characters max (LinkedIn limit)
- Specific to the company/role
- Not generic. Not "I'd love to connect."
- No emojis

Write only the note text.
"""


def draft_all(job: dict, profile: dict) -> dict:
    """
    Generate cover letter, email, and LinkedIn note for a job
    using the given profile's resume and voice.
    """
    cover_letter = _draft_cover_letter(job, profile)
    subject, email_body = _draft_email(job, profile)
    linkedin_note = _draft_linkedin_note(job, profile)

    return {
        "cover_letter":  cover_letter,
        "email_subject": subject,
        "email_body":    email_body,
        "linkedin_note": linkedin_note,
    }


def _get_name(profile: dict) -> str:
    resume = profile.get("resume") or ""
    name_line = next(
        (l for l in resume.splitlines() if l.strip().startswith("Name:")), ""
    )
    if name_line:
        return name_line.replace("Name:", "").strip()
    return profile.get("name", "")


def _get_signoff(profile: dict) -> str:
    name = _get_name(profile)
    return name.split()[0] if name else "Best"


def _draft_cover_letter(job: dict, profile: dict) -> str:
    prompt = COVER_LETTER_PROMPT.format(
        voice=profile.get("voice") or "Professional and direct.",
        resume=profile.get("resume") or "",
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        description=(job.get("description", "") or "")[:4000],
        signoff=_get_signoff(profile),
    )
    try:
        response = _client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"[Draft failed: {e}]"


def _draft_email(job: dict, profile: dict) -> tuple[str, str]:
    resume = profile.get("resume") or ""
    resume_brief = "\n".join(
        [l for l in resume.strip().splitlines() if l.strip()][:12]
    )

    prompt = EMAIL_PROMPT.format(
        voice=profile.get("voice") or "Professional and direct.",
        resume_brief=resume_brief,
        title=job.get("title", ""),
        company=job.get("company", ""),
        signoff=_get_signoff(profile),
    )
    try:
        response = _client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if "SUBJECT:" in text and "BODY:" in text:
            parts = text.split("BODY:", 1)
            subject = parts[0].replace("SUBJECT:", "").strip()
            body = parts[1].strip()
            return subject, body
        return "Application – " + job.get("title", "Role"), text
    except Exception as e:
        return "Application", f"[Draft failed: {e}]"


def _draft_linkedin_note(job: dict, profile: dict) -> str:
    resume = profile.get("resume") or ""
    # Build a brief summary from first few lines
    lines = [l.strip() for l in resume.splitlines() if l.strip()]
    summary = ". ".join(lines[2:5]) if len(lines) > 4 else profile.get("name", "")

    prompt = LINKEDIN_NOTE_PROMPT.format(
        title=job.get("title", ""),
        company=job.get("company", ""),
        name=_get_name(profile),
        summary=summary[:200],
        voice=profile.get("voice") or "Professional and direct.",
    )
    try:
        response = _client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()[:300]
    except Exception as e:
        return f"[Draft failed: {e}]"
