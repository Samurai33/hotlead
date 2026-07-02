# Accounts Pool — Page Overrides

> Route: `frontend/app/accounts/page.tsx`
> Rules here **override** `design-system/hotlead/MASTER.md`. Everything not listed follows the Master.

## Layout

- Grid of account `.card`s (`grid md:grid-cols-2 lg:grid-cols-3 gap-4`), each card: `@username` in `font-mono`, status badge, `requests_today / 200` usage meter, proxy indicator, last-used relative time, Delete `.btn-ghost` in `status-error` color with confirm dialog.
- "Add account" `.btn-primary` in the header opens the add form (username + session JSON + proxy URL).

## Status semantics (account pool, not job lifecycle)

| Account status | Color token |
|----------------|-------------|
| active | `status-running` (green) |
| cooldown | `status-paused` (amber) + `cooldown_until` countdown in `font-mono` |
| banned | `status-error` (red) |

## Usage meter

- 4px bar: `bg-brand` under 150 req, `status-paused` 150–180, `status-error` above 180 (hard limit 200/h — mirrors anti-ban rules).
- Count in `font-mono tabular-nums`.

## Security rules (UI-enforced)

- **Never render `session_json`** — not in cards, not in edit forms, not in tooltips. The API already omits it; the UI must not ask for it back.
- Session JSON textarea (add form only) is masked after paste and cleared on submit.
- Proxy URLs render with credentials masked (`http://user:•••@host:port`).
