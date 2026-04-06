# Apex Agent

AI-powered job search agent. Searches LinkedIn, scores matches with Claude, drafts cover letters and outreach — all through a web dashboard.

Multi-user: share one deployment with friends. Each person gets their own profile, resume, and job pipeline.

## How it works

1. **Search** — scans LinkedIn for jobs matching your target roles and locations
2. **Score** — Claude rates each job 0-100 against your resume with reasoning
3. **Draft** — generates a tailored cover letter, email, and LinkedIn note per job
4. **Review** — approve, edit, or skip from the dashboard

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/idyeah-studio/apex-agent.git
cd apex-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up Supabase (free)

1. Create a project at [supabase.com](https://supabase.com)
2. Go to SQL Editor, paste the contents of `schema.sql`, and run it
3. Copy your project URL and anon key from Settings > API

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your Anthropic API key and Supabase credentials
```

### 4. Start the server

```bash
python server.py
```

Open [http://localhost:5050](http://localhost:5050). Create a profile, fill in your resume and target roles in Settings, then click Run Agent.

## Deploy (share with friends)

Deploy to any platform that runs Python. Your friends just open the URL — no API keys or setup needed on their end.

### Render (free tier)

1. Push to GitHub
2. Go to [render.com](https://render.com) > New Web Service > connect your repo
3. Set environment variables: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
4. Deploy — you get a public URL like `https://apex-agent-xxx.onrender.com`

### Docker

```bash
docker build -t apex-agent .
docker run -p 5050:5050 --env-file .env apex-agent
```

### Railway / Fly.io

Both auto-detect the `Procfile`. Set env vars in their dashboard.

## Dashboard

- **Pipeline** — all jobs, filterable by status (New, Reviewed, Applied, Skipped)
- **Score** — click per-job or "Score All" to rate matches against your resume
- **Review** — cover letter, email, LinkedIn note with inline editing
- **Approve / Skip** — move jobs through your pipeline
- **Settings** — profile editor (resume, roles, locations, voice, dream companies)
- **Multi-user** — each person creates their own profile, data is isolated

## Project structure

```
server.py          — API server, serves dashboard + proxies Supabase
index.html         — single-file dashboard (HTML + CSS + JS)
run.py             — CLI entry point
src/
  agent.py         — search orchestrator
  search.py        — LinkedIn scraper with location filtering
  scorer.py        — Claude scoring (0-100 + reasoning)
  drafter.py       — Claude cover letter / email / LinkedIn note generation
  database.py      — Supabase read/write operations
  email_agent.py   — Gmail polling (optional)
schema.sql         — Supabase table definitions
config.py          — legacy config (profiles are now stored in Supabase)
Dockerfile         — container build
Procfile           — for Render / Railway / Heroku
```

## Cost

| Service | Cost |
|---------|------|
| LinkedIn search | Free (public scraping) |
| Claude API (scoring + drafting) | ~$0.01-0.05 per job |
| Supabase | Free tier (500MB, 50k rows) |
| Hosting (Render free tier) | Free |

## Contributing

1. Fork the repo
2. Create a feature branch from `develop`
3. Submit a PR to `develop`

`main` is protected — all changes go through PRs.

## License

MIT — see [LICENSE](LICENSE).
