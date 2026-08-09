# Frontend — Agent Guide

> Scope: `frontend/` only. Root `AGENTS.md` + `BUILD_SPEC.md` §§10–11 still apply.

## Stack

Vite + React + TypeScript + TanStack Query. Mobile-first — `390×844` must be excellent, desktop stays usable.

## What to Build (Section 11)

Vertical slice: start → signal → inspect markets/rivals → one major action → commit → outcome reveal → understand why → continue (5 turns).

Required screen content: age/chapter label, turn, cash, empire growth indicator, hero/world-state (placeholder OK), current signal, 2–4 action buttons, Home Valley pulse, River Town pulse, route status, Mira + Daran headlines, outcome reveal, completion summary.

## API Contract

Backend is source of truth. Frontend sends commands, never state mutations.

```
POST /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/{game_id}/choices/{choice_id}  # body: { expected_revision }
```

- Consume `GameView` (game_id, revision, turn, signal, player/empire/market summaries, route, rival headlines, choices, outcome). Never recompute economy.
- `expected_revision` is optimistic concurrency — stale revision must surface conflict, not silently overwrite.
- Prevent double-submit on commit.

## UI Principles

- Cards / typography / hierarchy over dense tables. Required decision info on main screen; detail views are optional depth.
- Outcome reveal is a payoff moment: time advances → world changes → numbers → top drivers (≤3) → causal why → rivals → next threat.
- Empire tableau shows compounding (names, scale, operation counts) — no free building placement.
- No multi-tab dashboard maze.

## Testing

Limited Playwright only — critical path:

1. Start + finish 5-turn game on mobile viewport
2. Desktop smoke test
3. Screenshots: first decision, drought warning turn, drought reveal, final summary
4. Zero console errors on critical path

```bash
npm run dev          # Vite
npx playwright test  # critical path only
```

No coverage gate on UI.

## When to Build

Not until `BUILD_SPEC.md` Section 11. Before that `frontend/` may stay empty. Keep `VITE_API_URL` env for Render static hosting.
