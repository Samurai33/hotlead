#!/usr/bin/env python3
"""
Add an Instagram account to the HotLead pool.

Usage:
    python scripts/add_account.py <username> [--proxy http://user:pass@host:port]

Security:
    - Password is read interactively (never passed as an argument, never stored)
    - Only the session JSON is persisted (device fingerprint + cookies)
    - The session is validated against Instagram before it is stored

Anti-ban:
    - ALWAYS log in through the SAME proxy the account will use at runtime.
      The session/device is tied to the IP it was created from; logging in from
      the server IP and then scraping through a proxy is a classic ban signal.
"""

import argparse
import getpass
import json
import os
import sys


def _challenge_code_handler(username: str, choice) -> str:
    """Resolve an SMS/email verification challenge inline.

    instagrapi calls this when Instagram sends a code during login. Returning
    the code here lets the login continue instead of dead-ending on
    ChallengeRequired. `choice` is a ChallengeChoice (SMS / EMAIL).
    """
    label = getattr(choice, "name", str(choice))
    return input(f"   Verification code ({label}) sent to @{username}: ").strip()


def _dump_ig_error(cl, exc) -> None:
    """Surface the RAW Instagram response so we can tell a genuine bad password
    from a masked block (checkpoint / challenge / rate-limit). IG frequently
    returns 'bad_password' when it is really refusing an automated login."""
    print(f"   ↳ exception: {type(exc).__name__}: {exc}")
    last = getattr(cl, "last_json", None)
    if isinstance(last, dict) and last:
        for key in (
            "message",
            "error_type",
            "error_title",
            "two_factor_required",
            "challenge",
            "checkpoint_url",
            "feedback_message",
            "feedback_title",
            "status",
        ):
            if key in last:
                print(f"   ↳ IG.{key}: {last[key]}")
        print(f"   ↳ raw (trimmed): {json.dumps(last)[:600]}")
    else:
        print("   ↳ no raw IG response captured (cl.last_json empty)")


def main():
    parser = argparse.ArgumentParser(description="Add Instagram account to HotLead pool")
    parser.add_argument("username", help="Instagram username (without @)")
    parser.add_argument("--proxy", default=None, help="Proxy URL (STRONGLY recommended)")
    args = parser.parse_args()

    username = args.username.lstrip("@")

    print(f"\n🔐 Adding @{username} to the HotLead account pool")
    print("   The password is used once to create a session — it is NEVER stored.\n")

    if not args.proxy:
        print("⚠️  No --proxy given. The session will be created from THIS host's IP.")
        print("   If the account scrapes through a proxy later, the IP mismatch is a")
        print("   ban signal. Strongly consider re-running with --proxy.\n")

    password = getpass.getpass(f"Instagram password for @{username}: ")

    print("\n📱 Logging in to Instagram...")

    try:
        from instagrapi import Client
        from instagrapi.exceptions import BadPassword, ChallengeRequired, TwoFactorRequired

        cl = Client()
        # Resolve SMS/email code challenges inline instead of aborting.
        cl.challenge_code_handler = _challenge_code_handler
        if args.proxy:
            cl.set_proxy(args.proxy)
            print(f"   Using proxy: {args.proxy}")

        try:
            cl.login(username, password)
        except TwoFactorRequired:
            code = input("   Enter 2FA code (authenticator/SMS): ").strip()
            cl.login(username, password, verification_code=code)
        except BadPassword as exc:
            print("❌ Instagram rejected the login as 'bad password'.")
            print("   ⚠️  This is OFTEN a masked block of an automated / new-device")
            print("      login, NOT necessarily a wrong password. Raw response:")
            _dump_ig_error(cl, exc)
            sys.exit(1)
        except ChallengeRequired as exc:
            # Reached only when the challenge can't be solved by a code (e.g. it
            # needs in-app approval). The code path is handled by the handler above.
            print("⚠️  Instagram requires in-app verification for this login.")
            print("   Open the Instagram app, approve the login attempt, then retry.")
            _dump_ig_error(cl, exc)
            sys.exit(1)

        # Best practice: confirm the fresh session actually works before storing.
        # A session that can't read the timeline is dead on arrival.
        cl.get_timeline_feed()
        session_json = json.dumps(cl.get_settings())
        print("✅ Login successful and session validated!")

        api_url = os.getenv("API_URL", "http://localhost:8000")
        api_key = os.getenv("API_KEY")

        if not api_key:
            # No API key in env → save the session to a gitignored file so it can
            # be imported later via POST /api/v1/accounts. Filename matches the
            # `*.session.json` rule in .gitignore so it never lands in git.
            from pathlib import Path

            out = Path(f"{username}.session.json")
            out.write_text(session_json)
            print("\n📋 API_KEY not set — session saved locally instead of POSTed:")
            print(f"   File: {out}  ({len(session_json)} chars)")
            print("   Import it with POST /api/v1/accounts, then DELETE the file.")
            return

        import httpx

        # Trailing slash: the route is POST /api/v1/accounts/ — without it FastAPI
        # 307-redirects, and httpx does NOT follow redirects by default, so the
        # POST body would be dropped. follow_redirects=True is belt-and-suspenders.
        resp = httpx.post(
            f"{api_url}/api/v1/accounts/",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"username": username, "session_json": session_json, "proxy_url": args.proxy},
            follow_redirects=True,
        )
        resp.raise_for_status()

        account = resp.json()
        print("\n🎉 Account added successfully!")
        print(f"   ID: {account['id']}")
        print(f"   Username: @{account['username']}")
        print(f"   Status: {account['status']}")

    except ImportError:
        print("❌ instagrapi not installed. Run: pip install instagrapi")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error [{type(e).__name__}]: {e}")
        try:
            _dump_ig_error(cl, e)
        except NameError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
