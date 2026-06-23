#!/usr/bin/env python3
"""
Add an Instagram account to the HotLead pool.

Usage:
    python scripts/add_account.py <username> [--proxy http://user:pass@host:port]

Security:
    - Password is read interactively (never passed as argument)
    - Only session JSON is stored in the database (no password)
    - Session JSON is saved immediately after login
"""
import argparse
import getpass
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def main():
    parser = argparse.ArgumentParser(description="Add Instagram account to HotLead pool")
    parser.add_argument("username", help="Instagram username (without @)")
    parser.add_argument("--proxy", default=None, help="Proxy URL (optional)")
    args = parser.parse_args()

    username = args.username.lstrip("@")

    print(f"\n🔐 Adding @{username} to HotLead account pool")
    print("   Password will NOT be stored — only session cookies.\n")

    password = getpass.getpass(f"Instagram password for @{username}: ")

    print("\n📱 Logging in to Instagram...")

    try:
        from instagrapi import Client
        from instagrapi.exceptions import BadPassword, ChallengeRequired, TwoFactorRequired

        cl = Client()
        if args.proxy:
            cl.set_proxy(args.proxy)
            print(f"   Using proxy: {args.proxy}")

        try:
            cl.login(username, password)
        except TwoFactorRequired:
            code = input("   Enter 2FA code: ").strip()
            cl.login(username, password, verification_code=code)
        except BadPassword:
            print("❌ Wrong password. Please try again.")
            sys.exit(1)
        except ChallengeRequired:
            print("⚠️  Instagram is requesting verification.")
            print("   Please complete the challenge in the Instagram app, then retry.")
            sys.exit(1)

        session_json = json.dumps(cl.get_settings())
        print("✅ Login successful!")

        # Save via API
        import httpx
        import os

        api_url = os.getenv("API_URL", "http://localhost:8000")
        api_key = os.getenv("API_KEY")

        if not api_key:
            # Fallback: print session for manual input
            print("\n📋 Session JSON (copy this to add via API):")
            print(f"   Username: @{username}")
            print(f"   Session length: {len(session_json)} chars")
            print("\n   Use the POST /api/v1/accounts endpoint with this session_json.")

            # Save to file as backup
            out = Path(f"session_{username}.json")
            out.write_text(session_json)
            print(f"   Session saved to: {out} (delete after importing!)")
            return

        resp = httpx.post(
            f"{api_url}/api/v1/accounts",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"username": username, "session_json": session_json, "proxy_url": args.proxy},
        )
        resp.raise_for_status()

        account = resp.json()
        print(f"\n🎉 Account added successfully!")
        print(f"   ID: {account['id']}")
        print(f"   Username: @{account['username']}")
        print(f"   Status: {account['status']}")

    except ImportError:
        print("❌ instagrapi not installed. Run: pip install instagrapi")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
