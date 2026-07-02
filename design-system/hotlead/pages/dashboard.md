# Dashboard (Jobs List) — Page Overrides

> Route: `frontend/app/page.tsx`
> Rules here **override** `design-system/hotlead/MASTER.md`. Everything not listed follows the Master.

## Layout

- Max width `max-w-7xl mx-auto`, page padding `p-6` (desktop) / `p-4` (mobile).
- Top row: 4 stat cards (`grid grid-cols-2 lg:grid-cols-4 gap-4`) — total jobs, running, emails found, phones found. Stat values in `font-mono text-2xl`.
- Below: jobs list as `.card` rows (not a bare table) — profile `@username` in `font-mono`, mode badge, status badge, progress bar, relative timestamp in `text-text-secondary`.

## Components

- **Status badge:** `rounded-full px-2 py-0.5 text-xs` with `bg-{status}/15 text-{status}` + label text. Running status may pulse a 6px dot (disable under `prefers-reduced-motion`).
- **Progress bar:** 4px height, `bg-surface-elevated` track, `bg-brand` fill, animate `width` via `transition-[width] duration-500`.
- **Primary CTA:** single "New job" `.btn-primary` in the header — the only green button on the page.
- Empty state: centered in a `.card`, muted icon + one sentence + "New job" CTA.

## Behavior

- List polls; rows must keep stable height while counts update (no skeleton swap after first load).
- Row click navigates to job detail — whole row is clickable (`cursor-pointer hover:bg-surface-elevated`).
