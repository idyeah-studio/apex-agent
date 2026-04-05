# ═══════════════════════════════════════════════════
#  APEX AGENT — CONFIG
#  Edit this file. Everything the agent needs to know
#  about you lives here.
# ═══════════════════════════════════════════════════

# ── Search targets ───────────────────────────────────
TARGET_ROLES = [
    "Principal UX Designer",
    "Staff Product Designer",
    "Staff UX Designer",
    "Head of Design",
    "Design Director",
]

LOCATIONS = [
    "San Francisco, CA",
    "Cupertino, CA",
    "Remote",
]

# ── LinkedIn auth ────────────────────────────────────
# Paste your li_at cookie value here (see README for how to get it)
# This lets the agent search as your logged-in account — more results,
# less rate limiting, access to salary data.
LINKEDIN_LI_AT = "REDACTED_LINKEDIN_COOKIE"   # e.g. "AQEDATd8vgAA..."

# ── Search settings ──────────────────────────────────
# Jobs per role × location combo (LinkedIn returns 25 per page)
# 25 = 1 page, 50 = 2 pages, 75 = 3 pages
RESULTS_PER_SEARCH = 50

# ── Scoring ──────────────────────────────────────────
# Jobs below this score are silently discarded (0–100)
SCORE_THRESHOLD = 62

# ── Salary filter ────────────────────────────────────
MIN_SALARY = 200_000   # USD annual, 0 to disable
MAX_SALARY = 0          # 0 = no cap

# ── Your resume ──────────────────────────────────────
# Paste the key facts Claude uses for scoring + drafting.
# No need to paste the full formatted resume — structured
# prose is fine.

RESUME = """
Name: Vishal Mehta
Email: vishal@idyeah.studio
Portfolio: vishalme.com

SUMMARY
25+ years at the intersection of product design and software engineering.
Currently contracted to Apple via Wipro as a senior UX designer in Cupertino.
Founder of IDYeah Studio LLC — a boutique design consultancy.
IEEE Senior Member. EB1A Green Card (Extraordinary Ability).

NOTABLE CLIENTS
Apple, Walmart, Intuitive Surgical, Mercedes, Raymond, Essar

CORE STRENGTHS
- End-to-end product design: research → IA → interaction → visual → handoff
- AI-augmented design workflows and tooling
- Design systems at scale across complex platforms
- Cross-functional leadership: eng, PM, research, C-suite
- Deep software engineering background (full-stack, SwiftUI, Figma, design tokens)
- Exceptional communicator; strong narrative framing for design rationale

WHAT I'M LOOKING FOR
- Senior IC or design leadership at a product-led company
- Domains: AI, health tech, enterprise software, or ambitious consumer
- Compensation: RSUs + bonus expected at this seniority (total comp 300K+)
- Culture: values craft, gives design a real seat at the table
- Logistics: hybrid or remote, Bay Area or NYC preferred

WHAT I WANT TO AVOID
- Purely agency or staff-aug roles
- Companies that treat design as decoration or post-engineering
- Execution-only IC roles with no strategic input
- Titles that undervalue 25 years of seniority
"""

# ── Voice for drafting ───────────────────────────────
VOICE = """
Writing style: Direct and confident. Story-driven, never listicle.
Tone: Warm but not eager. Assured but not arrogant.
Avoid: Buzzwords ("passionate about", "synergy", "leverage"),
       bullet-heavy structures, excessive self-promotion.
Length: Cover letters = 3 short paragraphs max. Emails = even shorter.
Sign off as: Vishal
"""

# ── Companies to skip ────────────────────────────────
# Agent will skip any job from these companies
BLOCKLIST = [
    # "Meta",
    # "TikTok",
]

# ── Dream companies (score bonus) ───────────────────
# Jobs from these companies get +10 to their score
DREAM_COMPANIES = [
    "Apple",
    "Stripe",
    "Linear",
    "Notion",
    "Figma",
    "Anthropic",
    "OpenAI",
    "Vercel",
]
