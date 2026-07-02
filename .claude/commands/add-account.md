---
description: Guide adding an Instagram account to the pool (session-only, no password stored)
argument-hint: [username]
---

Help the user add an Instagram account to the HotLead pool: **$ARGUMENTS**

Follow this exact procedure (delegate technical steps to `scraper-specialist`):

1. Explain the security model first: the password is used ONCE, locally, only to generate a `session_json` — it is never stored, never sent to the API, never logged.
2. Use `backend/scripts/add_account.py` as the mechanism. Run it inside the api container:
   `docker compose exec api python scripts/add_account.py`
   It performs the interactive login via instagrapi and POSTs `{username, session_json, proxy_url}` to `/api/v1/accounts`.
3. If the account has 2FA, the script will prompt for the code — that's expected.
4. If `ChallengeRequired` occurs during login: instruct the user to open the Instagram app, approve the login attempt, then retry.
5. Strongly recommend a dedicated proxy per account (`proxy_url`) — accounts sharing the server IP get banned together.
6. Verify: `GET /api/v1/accounts` shows the account as `active` and confirm `session_json` is NOT present in the response.
