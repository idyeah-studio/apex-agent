"""
Apex Agent — API Server
Serves the dashboard and proxies all Supabase operations so the
frontend never needs API keys.

Run: python3 server.py
Then open: http://localhost:5050/
"""

import threading
import subprocess
import sys
import os
import json
import re
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("PORT", 5050))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

agent_status = {
    "running": False,
    "log": [],
    "last_run": None,
    "jobs_found": 0,
    "profile_id": None,
}
agent_process = None  # track subprocess so we can kill it


# ── Supabase helper ─────────────────────────────────────
def supa_request(path, method="GET", body=None):
    """Make a request to Supabase REST API."""
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    # Fetch up to 10000 rows
    if method == "GET":
        req.add_header("Range", "0-9999")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._cors_headers()
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        # ── Static ──────────────────────────────────
        if path in ("/", "/index.html"):
            return self._serve_html()

        # ── API routes ──────────────────────────────
        if path == "/api/health":
            return self._json({"ok": True})

        if path == "/api/status":
            return self._json(agent_status)

        if path == "/api/profiles":
            rows = supa_request("profiles?select=id,name,created_at&order=created_at.asc")
            return self._json(rows)

        if path.startswith("/api/profiles/") and path.count("/") == 3:
            pid = path.split("/")[3]
            rows = supa_request(f"profiles?id=eq.{pid}")
            return self._json(rows[0] if rows else None)

        if path.startswith("/api/profiles/") and path.endswith("/jobs"):
            pid = path.split("/")[3]
            rows = supa_request(
                f"jobs?profile_id=eq.{pid}&select=*,drafts(*)&order=score.desc,found_at.desc"
            )
            return self._json(rows)

        if path.startswith("/api/profiles/") and path.endswith("/emails"):
            pid = path.split("/")[3]
            rows = supa_request(
                f"email_threads?profile_id=eq.{pid}&order=received_at.desc"
            )
            return self._json(rows)

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/profiles":
            rows = supa_request("profiles", method="POST", body=body)
            return self._json(rows[0] if rows else None, 201)

        if path == "/api/run":
            pid = body.get("profile_id") if body else None
            if not pid:
                return self._json({"ok": False, "message": "profile_id required"}, 400)
            if agent_status["running"]:
                return self._json({"ok": False, "message": "Agent already running"}, 409)
            threading.Thread(target=_run_agent, args=(pid,), daemon=True).start()
            return self._json({"ok": True, "message": "Agent started"})

        if path == "/api/stop":
            _stop_agent()
            return self._json({"ok": True, "message": "Agent stopped"})

        if path == "/api/clear-jobs":
            pid = body.get("profile_id") if body else None
            if not pid:
                return self._json({"ok": False, "message": "profile_id required"}, 400)
            supa_request(f"drafts?profile_id=eq.{pid}", method="DELETE")
            supa_request(f"jobs?profile_id=eq.{pid}", method="DELETE")
            return self._json({"ok": True, "message": "All jobs cleared"})

        # POST /api/jobs/:id/score — score + draft a single job
        if path.startswith("/api/jobs/") and path.endswith("/score"):
            jid = path.split("/")[3]
            pid = body.get("profile_id") if body else None
            if not pid:
                return self._json({"ok": False, "message": "profile_id required"}, 400)
            threading.Thread(target=_score_job, args=(jid, pid), daemon=True).start()
            return self._json({"ok": True, "message": "Scoring started"})

        # POST /api/score-all — score all unscored jobs for a profile
        if path == "/api/score-all":
            pid = body.get("profile_id") if body else None
            if not pid:
                return self._json({"ok": False, "message": "profile_id required"}, 400)
            threading.Thread(target=_score_all_jobs, args=(pid,), daemon=True).start()
            return self._json({"ok": True, "message": "Scoring all unscored jobs"})

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        path = urlparse(self.path).path
        body = self._read_body()

        # PATCH /api/profiles/:id
        if path.startswith("/api/profiles/") and path.count("/") == 3:
            pid = path.split("/")[3]
            rows = supa_request(f"profiles?id=eq.{pid}", method="PATCH", body=body)
            return self._json(rows[0] if rows else None)

        # PATCH /api/jobs/:id
        if path.startswith("/api/jobs/") and path.count("/") == 3:
            jid = path.split("/")[3]
            rows = supa_request(f"jobs?id=eq.{jid}", method="PATCH", body=body)
            return self._json(rows[0] if rows else None)

        # PATCH /api/drafts/:id
        if path.startswith("/api/drafts/") and path.count("/") == 3:
            did = path.split("/")[3]
            rows = supa_request(f"drafts?id=eq.{did}", method="PATCH", body=body)
            return self._json(rows[0] if rows else None)

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        path = urlparse(self.path).path

        # DELETE /api/profiles/:id
        if path.startswith("/api/profiles/") and path.count("/") == 3:
            pid = path.split("/")[3]
            supa_request(f"profiles?id=eq.{pid}", method="DELETE")
            return self._json({"ok": True})

        self.send_response(404)
        self.end_headers()

    # ── Helpers ──────────────────────────────────────

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length).decode())
        return None

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
        try:
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress access logs


# ── Agent runner ─────────────────────────────────────────

def _run_agent(profile_id):
    global agent_status, agent_process
    agent_status["running"] = True
    agent_status["profile_id"] = profile_id
    agent_status["log"] = ["Starting agent..."]
    agent_status["jobs_found"] = 0

    try:
        cmd = [sys.executable, "run.py", "search", "--profile", profile_id]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        agent_process = process

        for line in process.stdout:
            line = line.rstrip()
            if not line:
                continue
            clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
            agent_status["log"].append(clean)

            match = re.search(r"Found (\d+) unique jobs", clean)
            if match:
                agent_status["jobs_found"] = int(match.group(1))

            if len(agent_status["log"]) > 300:
                agent_status["log"] = agent_status["log"][-300:]

        process.wait()
        agent_status["last_run"] = datetime.datetime.now().isoformat()
        agent_status["log"].append(
            f"✓ Done. {agent_status['jobs_found']} jobs found and saved."
        )

    except Exception as e:
        agent_status["log"].append(f"Error: {e}")
    finally:
        agent_status["running"] = False
        agent_status["profile_id"] = None
        agent_process = None


def _stop_agent():
    global agent_process, agent_status
    if agent_process and agent_process.poll() is None:
        agent_process.terminate()
        try:
            agent_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent_process.kill()
        agent_status["log"].append("Agent stopped by user.")
    agent_status["running"] = False
    agent_status["profile_id"] = None
    agent_process = None


def _score_job(job_id, profile_id):
    """Score a single job and generate drafts."""
    from src import scorer, drafter, database as db

    profile = db.get_profile(profile_id)
    if not profile:
        return

    # Fetch the job
    rows = supa_request(f"jobs?id=eq.{job_id}&select=*")
    if not rows:
        return
    job = rows[0]

    # Score
    result = scorer.score_job(job, profile)
    dream_companies = profile.get("dream_companies") or []
    score = int(result.get("score", 0))
    if job.get("company") in dream_companies:
        score = min(100, score + 10)

    # Update job with score
    supa_request(f"jobs?id=eq.{job_id}", method="PATCH", body={
        "score": score,
        "score_reasoning": result.get("score_reasoning", ""),
    })

    # Generate drafts
    job["score"] = score
    job["score_reasoning"] = result.get("score_reasoning", "")
    drafts = drafter.draft_all(job, profile)
    drafts["job_id"] = job_id
    drafts["profile_id"] = profile_id
    # Remove any existing draft for this job first
    try:
        supa_request(f"drafts?job_id=eq.{job_id}", method="DELETE")
    except Exception:
        pass
    supa_request("drafts", method="POST", body=drafts)


def _score_all_jobs(profile_id):
    """Score all unscored jobs for a profile."""
    rows = supa_request(
        f"jobs?profile_id=eq.{profile_id}&score=is.null&select=id"
    )
    for row in (rows or []):
        _score_job(row["id"], profile_id)


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n  Apex Agent server → http://localhost:{PORT}/")
    print("  Ctrl+C to stop\n")
    HTTPServer((host, PORT), Handler).serve_forever()
