# Apex Agent

**AI-powered job search agent for senior design leaders.**
Search → Score → Draft → Review → Apply.

---

## Stack
| Layer | Tool | Cost |
|-------|------|------|
| Job search | `python-jobspy` | Free |
| Scoring + drafting | Claude API (`claude-opus-4-5`) | ~$0.50–2/day |
| Database | Supabase (free tier) | Free |
| Email | Gmail OAuth | Free |
| Dashboard | Local HTML file | Free |

**Total: ~$1/day during active search. Nothing otherwise.**

---

## Setup (15 minutes)

### 1. Clone and install
```bash
git clone <your-repo>
cd apex-agent
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY
```

### 3. Set up Supabase
1. Create a free project at supabase.com
2. Go to SQL Editor → paste contents of `schema.sql` → Run

### 4. Customize config.py
Open `config.py` and update:
- Your resume in `RESUME`
- Your voice/tone in `VOICE`
- Dream companies in `DREAM_COMPANIES`
- Companies to skip in `BLOCKLIST`

### 5. Run your first search
```bash
python run.py search
```

### 6. Open the dashboard
Open `dashboard/index.html` in your browser.
Enter your Supabase URL + key in Settings → Save.
Your jobs appear instantly.

---

## Daily workflow

```
Morning: python run.py search
         → open dashboard → review top matches → approve drafts
         
Afternoon: python run.py email
           → open dashboard → email tab → approve replies
```

Or run on a schedule (every morning at 7am):
```bash
python run.py schedule
```

---

## Dashboard features
- **Pipeline view**: all jobs, filterable by status
- **Score cards**: Claude's 0–100 match score with reasoning
- **Draft review**: cover letter, email, LinkedIn note per job
- **Edit drafts**: click "Edit Drafts" to modify before approving
- **Email threads**: recruiter replies with Claude-drafted responses
- **One-click approve**: marks job as applied, saves edited drafts

---

## AIHawk attribution
This project's browser automation architecture is inspired by
[AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) (MIT License).
The scoring, drafting, multi-source search, and dashboard are original.

---

## Roadmap
- [ ] LinkedIn Easy Apply automation (Selenium, AIHawk-style)
- [ ] Calendar integration for interview scheduling
- [ ] Multi-user auth (Supabase Auth) for SaaS version
- [ ] Mobile companion (approve drafts from iPhone)
