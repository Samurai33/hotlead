# Prospects Table — Page Overrides

> Route: `frontend/app/jobs/[id]/prospects/page.tsx`
> Rules here **override** `design-system/hotlead/MASTER.md`. Everything not listed follows the Master.

## Layout

- Densest page in the app: full-width table inside a `.card` with `overflow-x-auto`; the page itself never scrolls horizontally.
- Toolbar above the table: filter inputs (`.input`, compact `text-sm`) for has-email / has-phone / is-business, search by username; Export CSV / Export JSON as `.btn-ghost` with download icon on the right.
- Columns: username (`font-mono`, sticky-left on mobile), full name, email, phone, website, followers (`font-mono tabular-nums`, right-aligned), flags (business/verified/private as small Lucide icons with `title`).

## Table rules

- Row height `h-10`, `text-sm`, zebra via `odd:bg-surface even:bg-surface/50`.
- Header row sticky (`sticky top-0 bg-surface-elevated z-10`).
- Empty cell = `—` in `text-text-muted` (never blank, never "null").
- Email/phone/website are copy-on-click with a subtle "copied" tooltip; external website link opens `target="_blank" rel="noopener"`.
- Pagination footer: `font-mono` range ("1–50 of 1.2k"), prev/next `.btn-ghost`.

## Anti-patterns (page-specific)

- ❌ Truncating emails without `title` attribute for the full value.
- ❌ Client-side filtering of server-paginated data — filters go through the API query params.
