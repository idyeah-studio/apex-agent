"""
Apex Agent — API Server
Serves the dashboard and proxies all Supabase operations.
All API routes (except auth) require a valid Supabase access token.

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
agent_process = None


# ── Supabase helpers ────────────────────────────────────
def supa_request(path, method="GET", body=None, token=None):
    """Make a request to Supabase REST API."""
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    # Use user token if provided, otherwise service key
    req.add_header("Authorization", f"Bearer {token or SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    if method == "GET":
        req.add_header("Range", "0-9999")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def supa_auth_request(endpoint, body):
    """Make a request to Supabase Auth API."""
    import urllib.request
    url = f"{SUPABASE_URL}/auth/v1/{endpoint}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.request.HTTPError as e:
        err_body = e.read().decode()
        try:
            return json.loads(err_body), e.code
        except json.JSONDecodeError:
            return {"error": err_body}, e.code


def supa_get_user(access_token):
    """Validate an access token and return the user object."""
    import urllib.request
    url = f"{SUPABASE_URL}/auth/v1/user"
    req = urllib.request.Request(url, method="GET")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


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
        if path == "/privacy":
            return self._serve_file("privacy.html", "text/html; charset=utf-8")

        # ── Public routes ───────────────────────────
        if path == "/api/health":
            return self._json({"ok": True})

        if path == "/api/status":
            return self._json(agent_status)

        # ── Auth-required routes ────────────────────
        user = self._get_auth_user()
        if not user:
            return self._json({"error": "Unauthorized"}, 401)
        user_id = user["id"]

        if path == "/api/me/profile":
            rows = supa_request(f"profiles?user_id=eq.{user_id}")
            return self._json(rows[0] if rows else None)

        if path == "/api/me/jobs":
            # Get profile for this user, then their jobs
            profiles = supa_request(f"profiles?user_id=eq.{user_id}&select=id")
            if not profiles:
                return self._json([])
            pid = profiles[0]["id"]
            rows = supa_request(
                f"jobs?profile_id=eq.{pid}&select=*,drafts(*)&order=score.desc.nullsfirst,found_at.desc"
            )
            return self._json(rows)

        if path == "/api/me/emails":
            profiles = supa_request(f"profiles?user_id=eq.{user_id}&select=id")
            if not profiles:
                return self._json([])
            pid = profiles[0]["id"]
            rows = supa_request(
                f"email_threads?profile_id=eq.{pid}&order=received_at.desc"
            )
            return self._json(rows)

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        # ── Auth routes (no token needed) ───────────
        if path == "/api/auth/signup":
            data, status = supa_auth_request("signup", body or {})
            return self._json(data, status if status < 400 else 400)

        if path == "/api/auth/login":
            data, status = supa_auth_request("token?grant_type=password", body or {})
            return self._json(data, status if status < 400 else 401)

        if path == "/api/auth/magic-link":
            data, status = supa_auth_request("magiclink", body or {})
            return self._json(data, status if status < 400 else 400)

        if path == "/api/auth/refresh":
            data, status = supa_auth_request("token?grant_type=refresh_token", body or {})
            return self._json(data, status if status < 400 else 401)

        # ── Auth-required routes ────────────────────
        user = self._get_auth_user()
        if not user:
            return self._json({"error": "Unauthorized"}, 401)
        user_id = user["id"]
        pid = self._get_profile_id(user_id)

        if path == "/api/me/profile":
            if pid:
                # Update existing
                rows = supa_request(f"profiles?user_id=eq.{user_id}", method="PATCH", body=body)
                return self._json(rows[0] if rows else None)
            else:
                # Create new
                body["user_id"] = user_id
                rows = supa_request("profiles", method="POST", body=body)
                return self._json(rows[0] if rows else None, 201)

        if path == "/api/run":
            if not pid:
                return self._json({"ok": False, "message": "Create a profile first"}, 400)
            if agent_status["running"]:
                return self._json({"ok": False, "message": "Agent already running"}, 409)
            threading.Thread(target=_run_agent, args=(pid,), daemon=True).start()
            return self._json({"ok": True, "message": "Agent started"})

        if path == "/api/stop":
            _stop_agent()
            return self._json({"ok": True, "message": "Agent stopped"})

        if path == "/api/clear-jobs":
            if not pid:
                return self._json({"ok": False, "message": "No profile"}, 400)
            supa_request(f"drafts?profile_id=eq.{pid}", method="DELETE")
            supa_request(f"jobs?profile_id=eq.{pid}", method="DELETE")
            return self._json({"ok": True, "message": "All jobs cleared"})

        # POST /api/jobs/:id/score
        if path.startswith("/api/jobs/") and path.endswith("/score"):
            jid = path.split("/")[3]
            if not pid:
                return self._json({"ok": False, "message": "No profile"}, 400)
            threading.Thread(target=_score_job, args=(jid, pid), daemon=True).start()
            return self._json({"ok": True, "message": "Scoring started"})

        if path == "/api/score-all":
            if not pid:
                return self._json({"ok": False, "message": "No profile"}, 400)
            threading.Thread(target=_score_all_jobs, args=(pid,), daemon=True).start()
            return self._json({"ok": True, "message": "Scoring all unscored jobs"})

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        path = urlparse(self.path).path
        body = self._read_body()

        user = self._get_auth_user()
        if not user:
            return self._json({"error": "Unauthorized"}, 401)

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

        user = self._get_auth_user()
        if not user:
            return self._json({"error": "Unauthorized"}, 401)

        self.send_response(404)
        self.end_headers()

    # ── Helpers ──────────────────────────────────────

    def _get_auth_user(self):
        """Extract and validate the Bearer token from the request."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        return supa_get_user(token)

    def _get_profile_id(self, user_id):
        """Get the profile ID for a user, or None."""
        rows = supa_request(f"profiles?user_id=eq.{user_id}&select=id")
        return rows[0]["id"] if rows else None

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length).decode())
        return None

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        self._serve_file("index.html", "text/html; charset=utf-8")

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


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

            match = re.search(r"(\d+) total saved", clean)
            if match:
                agent_status["jobs_found"] = int(match.group(1))

            if len(agent_status["log"]) > 300:
                agent_status["log"] = agent_status["log"][-300:]

        process.wait()
        agent_status["last_run"] = datetime.datetime.now().isoformat()
        agent_status["log"].append(
            f"Done. {agent_status['jobs_found']} jobs saved."
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

    rows = supa_request(f"jobs?id=eq.{job_id}&select=*")
    if not rows:
        return
    job = rows[0]

    result = scorer.score_job(job, profile)
    dream_companies = profile.get("dream_companies") or []
    score = int(result.get("score", 0))
    if job.get("company") in dream_companies:
        score = min(100, score + 10)

    supa_request(f"jobs?id=eq.{job_id}", method="PATCH", body={
        "score": score,
        "score_reasoning": result.get("score_reasoning", ""),
    })

    job["score"] = score
    job["score_reasoning"] = result.get("score_reasoning", "")
    drafts = drafter.draft_all(job, profile)
    drafts["job_id"] = job_id
    drafts["profile_id"] = profile_id
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
    print(f"\n  Apex Agent server -> http://localhost:{PORT}/")
    print("  Ctrl+C to stop\n")
    HTTPServer((host, PORT), Handler).serve_forever()
