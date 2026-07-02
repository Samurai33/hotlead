# Job Detail — Page Overrides

> Route: `frontend/app/jobs/[id]/page.tsx`
> Rules here **override** `design-system/hotlead/MASTER.md`. Everything not listed follows the Master.

## Layout

- Header: `@profile_username` in `font-mono text-xl`, mode + status badges inline, actions right-aligned (Pause/Resume `.btn-ghost`, Delete ghost in `status-error` color with confirm).
- Hero progress block in a `.card-elevated`: large progress bar (8px), `scraped_count / total_count` in `font-mono tabular-nums`, percentage right-aligned.
- Stat grid below (`grid grid-cols-2 lg:grid-cols-4 gap-4`): emails found, phones found, websites, elapsed time.
- Link to prospects table as a prominent `.card` row with count + chevron.

## Behavior

- Polls every ~2s while `running` — progress bar animates width only; numbers never reflow (fixed-width `tabular-nums`).
- `paused` state: bar fill switches to `status-paused`, Resume becomes the primary action.
- `error` state: `.card` with `border-status-error/40`, `error_message` in `font-mono text-sm`, retry guidance in `text-text-secondary`.
- Pause/Resume buttons disable while the request is in flight.

## Anti-patterns (page-specific)

- ❌ Full-page spinner on poll refresh — only initial load may skeleton.
- ❌ Toasts for progress updates — the bar IS the feedback.
