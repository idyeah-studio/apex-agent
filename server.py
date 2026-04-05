"""
Apex Agent — Local API Server
Lets the dashboard trigger the agent and continue paginated searches.

Run: python3 server.py
Then open: dashboard/index.html
"""

import threading
import subprocess
import sys
import os
import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("PORT", 5050))
agent_status = {
    "running": False,
    "log": [],
    "last_run": None,
    "jobs_found": 0,
}


class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            self._cors()
            self._json(agent_status)
        elif self.path == "/health":
            self._cors()
            self._json({"ok": True})
        elif self.path in ("/", "/index.html"):
            self._serve_html()
        else:
            self.send_response(404)
            self.end_headers()

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

    def do_POST(self):
        if self.path == "/run":
            self._cors()
            if agent_status["running"]:
                self._json({"ok": False, "message": "Agent already running"}, 409)
                return
            threading.Thread(target=_run_agent, args=("search",), daemon=True).start()
            self._json({"ok": True, "message": "Agent started"})

        elif self.path == "/continue":
            self._cors()
            if agent_status["running"]:
                self._json({"ok": False, "message": "Agent already running"}, 409)
                return
            threading.Thread(target=_run_agent, args=("search", "--continue"), daemon=True).start()
            self._json({"ok": True, "message": "Continuing search..."})

        else:
            self.send_response(404)
            self.end_headers()

    def _cors(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json")

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        if code != 200:
            self.send_response(code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # suppress access logs


def _run_agent(*args):
    global agent_status
    agent_status["running"] = True
    agent_status["log"] = ["Starting agent..."]
    agent_status["jobs_found"] = 0

    try:
        cmd = [sys.executable, "run.py"] + list(args)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        import re as _re
        for line in process.stdout:
            line = line.rstrip()
            if not line:
                continue
            clean = _re.sub(r"\x1b\[[0-9;]*m", "", line)
            agent_status["log"].append(clean)

            # Extract jobs found count from log output
            match = _re.search(r"Found (\d+) unique jobs", clean)
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


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n  Apex Agent server → http://localhost:{PORT}")
    print("  Dashboard:  http://localhost:{PORT}/")
    print("  Ctrl+C to stop\n")
    HTTPServer((host, PORT), Handler).serve_forever()
