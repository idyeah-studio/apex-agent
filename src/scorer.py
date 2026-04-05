"""
Claude scores each job against a profile's resume and preferences.
Returns a 0–100 score + plain-English reasoning.
"""

import anthropic
import json

_client = anthropic.Anthropic()


SCORE_PROMPT = """
You are a ruthlessly honest career advisor helping a candidate evaluate job opportunities.

## The candidate
{resume}

## The job
Title: {title}
Company: {company}
Location: {location}
Salary: {salary}
Source: {source}

Job description:
{description}

## Your task
Score this job from 0–100 for this specific candidate. Be honest and specific.

Scoring guide:
- 90–100: Near-perfect match. Right seniority, right domain, right culture signals, right comp.
- 70–89: Strong match with minor gaps. Worth applying.
- 50–69: Plausible but notable mismatches. Apply selectively.
- Below 50: Poor fit. Skip.

Dream company bonus: Add 10 points if the company is one of: {dream_companies}

Penalize heavily for:
- Junior titles or "junior" language in the JD
- Agency / staff-aug framing
- "We're a startup of 3" with director title
- Required skills that are clearly non-matching execution only roles
- Salary listed below candidate's minimum

Respond ONLY with a JSON object, no markdown, no explanation outside the JSON:
{{
  "score": <integer 0-100>,
  "reasoning": "<2-3 sentences. Be direct. What's good, what's a concern.>",
  "green_flags": ["<flag>", ...],
  "red_flags": ["<flag>", ...]
}}
"""


def score_job(job: dict, profile: dict) -> dict:
    """
    Score a job against a profile.
    Returns {"score": int, "reasoning": str} or defaults on error.
    """
    resume = profile.get("resume") or ""
    dream_companies = profile.get("dream_companies") or []

    salary_str = "Not listed"
    if job.get("salary_min"):
        salary_str = f"${job['salary_min']:,}"
        if job.get("salary_max"):
            salary_str += f"–${job['salary_max']:,}"

    prompt = SCORE_PROMPT.format(
        resume=resume,
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        salary=salary_str,
        source=job.get("source", ""),
        description=(job.get("description", "") or "")[:4000],
        dream_companies=", ".join(dream_companies),
    )

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)
        return {
            "score":          int(result.get("score", 0)),
            "score_reasoning": result.get("reasoning", ""),
        }

    except Exception as e:
        return {"score": 0, "score_reasoning": f"Scoring error: {e}"}
