---
description: Guide adding an Instagram account to the pool (session-only, no password stored)
argument-hint: [username]
---

Help the user add an Instagram account to the HotLead pool: **$ARGUMENTS**

Follow this exact procedure (delegate technical steps to `scraper-specialist`):

1. Explain the security model first: the password is used ONCE, locally, only to generate a `session_json` — it is never stored, never sent to the API, never logged.
2. Use `backend/scripts/add_account.py` as the mechanism. Run it **interactively** inside the api container (note the `-it`):
   `docker compose exec -it api python scripts/add_account.py <username> --proxy <proxy_url>`
   It logs in via instagrapi, validates the session (`get_timeline_feed`), and POSTs `{username, session_json, proxy_url}` to `/api/v1/accounts`.
3. If the account has 2FA, the script prompts for the authenticator/SMS code — that's expected.
4. If Instagram sends an SMS/email **verification code**, the script now asks for it inline (`challenge_code_handler`) — no need to abort. Only a challenge that needs **in-app approval** stops the script: open the Instagram app, approve the login, then retry.
5. Always pass `--proxy` — the session/device is tied to the IP it was created from, so onboard through the SAME proxy the account will use at runtime. Accounts sharing an IP get banned together.
6. Verify: `GET /api/v1/accounts` shows the account as `active` and confirm `session_json` is NOT present in the response.
