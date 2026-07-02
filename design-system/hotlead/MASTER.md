# HotLead — Design System MASTER

> **LOGIC:** When building a specific page, first check `design-system/hotlead/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

**Project:** HotLead — self-hosted Instagram audience scraper
**Style:** Data-Dense Dashboard · Dark Mode (OLED-friendly)
**Stack:** Next.js 14 App Router · Tailwind · shadcn/ui patterns
**Source of truth for tokens:** `frontend/tailwind.config.ts` + `frontend/app/globals.css` — this file documents them; never let the two drift.

---

## Global Rules

### Color Palette (tokens already defined in Tailwind)

| Role | Hex | Tailwind token |
|------|-----|----------------|
| Background (page) | `#020617` | `bg-background` |
| Surface (cards, inputs) | `#0F172A` | `bg-surface` |
| Surface elevated (hover, dropdowns) | `#1E293B` | `bg-surface-elevated` |
| Brand / CTA | `#22C55E` | `bg-brand` |
| Brand hover | `#16A34A` | `bg-brand-hover` |
| Brand muted (fills, badges) | `#166534` | `bg-brand-muted` |
| Text primary | `#F8FAFC` | `text-text` |
| Text secondary | `#94A3B8` | `text-text-secondary` |
| Text muted | `#475569` | `text-text-muted` |
| Border | `#1E293B` | `border-border` |
| Border subtle | `#0F172A` | `border-border-subtle` |

**Color notes:** deep-navy dark theme with a single green brand accent. Green is reserved for primary actions and "running/healthy" semantics — never use it decoratively.

### Status Colors (job lifecycle — semantic, do not repurpose)

| Status | Hex | Token |
|--------|-----|-------|
| pending | `#64748B` | `status-pending` |
| running | `#22C55E` | `status-running` |
| paused | `#F59E0B` | `status-paused` |
| done | `#3B82F6` | `status-done` |
| error | `#EF4444` | `status-error` |

Status is always shown with **color + label** (never color alone — a11y).

### Typography

- **Sans (UI, body):** Fira Sans — `font-sans`
- **Mono (data, counters, usernames, IDs, code):** Fira Code — `font-mono`
- **Mood:** technical, precise, data-first
- Numbers that update (scraped_count, emails_found) use `font-mono tabular-nums` to avoid layout jitter.
- Body text ≥ 14px (`text-sm`) on desktop density, 16px on mobile forms.

```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` / `p-1` | 4px | tight inline gaps |
| `gap-2` / `p-2` | 8px | icon gaps, badge padding |
| `gap-4` / `p-4` | 16px | card padding (`.card`), standard |
| `gap-6` / `p-6` | 24px | section padding |
| `gap-8` / `p-8` | 32px | page gutters |

High density is intentional: this is an operator dashboard, not a marketing site.

### Component Classes (defined in `globals.css` — reuse, don't reinvent)

| Class | Purpose |
|-------|---------|
| `.card` | `bg-surface border border-border rounded-lg p-4` |
| `.card-elevated` | same, on `bg-surface-elevated` |
| `.btn-primary` | brand bg, dark text, `transition-colors`, disabled state built-in |
| `.btn-ghost` | secondary text, hover elevates |
| `.input` | surface bg, brand focus ring, full width |

### Interaction Rules

- Transitions: `transition-colors duration-200`; never scale transforms that shift layout.
- Every clickable element: `cursor-pointer` + visible hover (color/bg, not motion).
- Focus: `focus:ring-1 focus:ring-brand` minimum, keyboard-visible everywhere.
- Async buttons disable while pending (`disabled:opacity-50 disabled:cursor-not-allowed`).
- Polling updates (job progress) must not flash or jump — reserve space, animate width of progress bars only.
- Respect `prefers-reduced-motion`: disable pulse/blink animations.

### Iconography

- Lucide (already the shadcn/ui default), `w-4 h-4` inline / `w-5 h-5` standalone, `viewBox 24x24`.
- Never emojis as icons.

---

## Anti-Patterns (Do NOT Use)

- ❌ Light backgrounds or white cards — the app is dark-mode only
- ❌ New hex values in components — extend `tailwind.config.ts` first, then document here
- ❌ Green for anything other than brand actions / running / success
- ❌ Color-only status indicators (always pair with a text label)
- ❌ Emojis as icons; mixed icon sets
- ❌ Layout-shifting hover (scale/translate on tables and cards in lists)
- ❌ Instant state changes (always 150–300ms transitions)
- ❌ Spinners without reserved space (content jumping during 2s polling)

---

## Pre-Delivery Checklist

- [ ] Tokens only from `tailwind.config.ts` (no ad-hoc hex)
- [ ] Status shown as color + label
- [ ] `cursor-pointer` + hover feedback on clickables
- [ ] Focus ring visible for keyboard nav
- [ ] Counters use `font-mono tabular-nums`
- [ ] Loading: skeleton/spinner with reserved space for ops > 300ms
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px — tables scroll horizontally inside `.card`, page never does
