#!/usr/bin/env python3
"""
Create a new Apex user account.

Usage:
  python scripts/create_user.py "John Doe" john@example.com

Creates a Supabase Auth user + profile with 30-day expiry.
Prints the credentials to send to the user.
"""

import sys
import os
import json
import string
import random
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]


def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.SystemRandom().choice(chars) for _ in range(length))


def supabase_admin_request(path, method="POST", body=None):
    url = f"{SUPABASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def create_user(name, email):
    password = generate_password()

    # 1. Create auth user (auto-confirm)
    user = supabase_admin_request("/auth/v1/admin/users", body={
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = user["id"]

    # 2. Create profile with 30-day expiry
    expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
    supabase_admin_request("/rest/v1/profiles", body={
        "user_id": user_id,
        "name": name,
        "expires_at": expires,
    })

    return {
        "name": name,
        "email": email,
        "password": password,
        "expires": expires[:10],
        "url": "https://apex.idyeah.studio",
    }


def main():
    if len(sys.argv) < 3:
        print('Usage: python scripts/create_user.py "Full Name" email@example.com')
        sys.exit(1)

    name = sys.argv[1]
    email = sys.argv[2]

    print(f"\nCreating account for {name} ({email})...\n")
    creds = create_user(name, email)

    print("=" * 50)
    print("  ACCOUNT CREATED")
    print("=" * 50)
    print(f"  Name:     {creds['name']}")
    print(f"  Email:    {creds['email']}")
    print(f"  Password: {creds['password']}")
    print(f"  Expires:  {creds['expires']}")
    print(f"  URL:      {creds['url']}")
    print("=" * 50)

    print("\n--- EMAIL TEMPLATE (copy below) ---\n")
    print(f"""Subject: Your Apex account is ready

Hi {name.split()[0]},

Your Apex account is ready. Here are your login details:

  URL:      {creds['url']}
  Email:    {creds['email']}
  Password: {creds['password']}

Quick start:
1. Sign in at the URL above
2. Go to Settings — paste your resume, add target roles and locations
3. Click "Run Agent" to start searching
4. Review results, click "Score" to get AI match ratings

Your access is valid for 30 days (until {creds['expires']}).

Please change your password after first login — go to Settings (coming soon) or let me know and I'll reset it.

If you run into anything, just reply to this email.

Vishal""")


if __name__ == "__main__":
    main()
