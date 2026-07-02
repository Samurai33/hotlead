# Login — Page Overrides

> Route: `frontend/app/(auth)/login/page.tsx`
> Rules here **override** `design-system/hotlead/MASTER.md`. Everything not listed follows the Master.

## Layout

- Single centered `.card-elevated` (`max-w-sm w-full`) on the bare `bg-background` — no navbar, no sidebar.
- Wordmark "HotLead" in `font-mono font-semibold` above the form; one-line descriptor in `text-text-secondary text-sm`.
- One field only: API key (`.input`, `type="password"`, `autocomplete="off"`, mobile font-size 16px to prevent iOS zoom) + `.btn-primary` full width ("Enter").

## Behavior

- Submit disables the button and shows inline spinner inside it (no page overlay).
- Invalid key: inline error under the field in `text-status-error text-sm`, input gets `border-status-error`; never a toast, never reveal whether the key format was close.
- On success: redirect to dashboard; key stored per `lib/auth.ts` (no changes to storage strategy from a design task).

## Anti-patterns (page-specific)

- ❌ Marketing content, illustrations, or gradients — this is an operator gate, keep it austere.
- ❌ "Show key" toggle — the key is a secret; paste-and-go.
