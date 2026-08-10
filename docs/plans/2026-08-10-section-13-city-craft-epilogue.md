# Section 13 — City & Craft Transition Epilogue — Plan

> Branch: `section/13-city-craft-epilogue` (already on). Authority: `BUILD_SPEC.md` §13 + `docs/plans/2026-08-10-section-13-design-direction.md` (Claude, design authority). Fixes AC1/AC2 measurement rule before running; extends engine+domain with minimal epilogue, same GameView, Section 11 UI reuse.

---

## 0. Reading list (what this plan rests on)

- `BUILD_SPEC.md:1546-1594` — §13 goal, 5 ACs, stop condition.
- `docs/plans/2026-08-10-section-13-design-direction.md` — bottleneck shift table, 1-resource/1-verb/1-curve minimum, 4 legacies, 3-turn budget, engine-first scope, AC1 harness instrument, AC2 binding-constraint proof.
- `STATE.md` §§ What exists / Boundaries / Last known green — `FiveTurnGame TURN_LIMIT=5`, `default_start_state` storage 130, `PlayerState{ cash, inventory.grain, farm, storage }`, `MarketState{ supply, demand, regional_output, base_price, current_price, responsiveness, max_movement_bps }`, `RouteState` 20/300/10000, `TURN_SPECS` 5 authored, `PressureState`, `harness.py` 5 policies `run_batch` integer-bps gates.
- `DECISIONS.md` 016/017/022/024/025 — matched controls, integer bps gates, no-strategy-gatekeeping, uncapped buy/sell, run-record instrumentation.
- `backend/app/engine/harness.py`, `prototype.py`, `turn.py`, `actor.py`, `domain/types.py`, `domain/trace.py`, `domain/pressure.py`, `api/schemas.py`, `api/mappers.py`.

---

## 1. Goal

Deliver the thesis: **land and storage still make grain, but grain stops being what the market wants.** Three epilogue turns after the 5-turn agriculture shift the binding constraint from `storage_capacity + drought timing` to `skilled_labour`; at least one agricultural winner measurably loses dominance. The epilogue is a hook, not a second game.

---

## 2. AC1 / AC2 measurement design — fixed before any run

### AC1 — "a previously strong Agricultural strategy becomes less dominant" (measurement, not claim)

**Instrument:** existing `backend/app/engine/harness.py` `run_batch` extended to an 8-turn variant (see §4). Same policy set, same seeds, paired runs so only the epilogue differs.

**Arms (four, paired — same seeds, same start_state, same first-5-turn policy code):**

- **Arm A — Agriculture only:** `FiveTurnGame` for 5 turns, existing `POLICY_FUNCS` over `POLICY_IDS` (5 policies, intentional 4). Record medians.
- **Arm B — Agriculture + Epilogue (full):** identical seeds, identical `start_state(seed, version)`, identical policy functions for turns 0-4, then 3 epilogue turns with demand shift 410→280→220→180 active, legacies active, and shared workshop/hire logic (see §5.5). Record medians. This is the regime-shift arm.
- **Control C — Epilogue without demand shift:** same as Arm B except raw-demand shift DISABLED (demand stays 410 all three epilogue turns), everything else identical (legacies active, craft/hire/sell logic identical). Isolation control for AC1.
- **Control L — Epilogue without legacies:** same as Arm B except legacies zeroed (no legacy effects applied), demand shift active. AC3 control: does the epilogue still behave differently without legacies?

**Policy set stays fixed.** No policy invented to lose. Both arms use `POLICY_IDS`; intentional ranking is over `INTENTIONAL_POLICY_IDS = (production_heavy, storage_heavy, trade_heavy, cash_preserving)`. `random_legal` stays in batch for price/negativity coverage but excluded from rank.

**Ranking metric:** median final wealth (integer `Money`, `wealth = cash + grain*home_price//1000 + finished_goods*finished_price//1000` — finished component 0 in Arm A). Computed as in `harness.py: median = sorted[mid] or avg of two mids`.

**Identify `P_agri`:** the top median among intentional 4 in Arm A. Example from current green (n=40): `storage_heavy 2345` > `production_heavy 2290` > `trade_heavy 2241` > `hold 2109` would make `P_agri = storage_heavy`. Published result may differ with larger n; `P_agri` is whatever Arm A measures — not assumed.

**Pass rule (write into code and gate before observing B):**

> **AC1 PASS iff** `P_agri` is no longer rank 1 in Arm B **OR** its median lead over the Arm B runner-up contracts by ≥ **40%** relative to its Arm A lead, **AND** Control C does **NOT** pass the same rule.
>
> Formal: let `lead_A = median(P_agri,A) - median(second_A,A)`, `lead_B = median(P_agri,B) - median(second_B,B)` (when `P_agri` still rank 1 in B; if rank>1, lead_B ≤0 and rule satisfied via rank drop). Define contraction `C = (lead_A - lead_B) * 100 // max(lead_A,1)`. **Pass if (`rank_B(P_agri) ≥2` or `C ≥40`) and Control C does NOT satisfy that disjunction for the same `P_agri`.** Report `rank_A, rank_B, rank_C, rank_L, medians, leads, C_B, C_C, median_ratio_bps` for all four arms. Require `n_seeds ≥200` for the published verdict (40-seed pilot allowed for tuning).

**AC1 credibility guard:** Control C (demand shift disabled) must NOT pass. If it does, the rank change is an artifact of extra turns / compounding, not the bottleneck shift, and AC1 is not credible even if Arm B passes. Control L (no legacies) is the AC3 control — report it but do not gate AC1 on it; legacies-zeroed passing would mean demand shift alone carries the thesis, which is legitimate for AC1.

**Net-positive guard (AC5 / Section 12 criterion 9):** At least one intentional policy's median final wealth in Arm B must be **higher** than its median in Arm A (`median_B > median_A`). Tune demand decay within ±20% and craft upside within the §6 constants until both AC1 and this guard hold. If they cannot both hold, report that — the decay is doing work the craft opportunity should be doing; the fix is a stronger `FINISHED_GOODS_PRICE` or `FINISHED_PER_GRAIN`, not a gentler demand curve.

Rationale: 40% is large enough to be legible to a player (a former 15% lead becoming ~8%), small enough that a real bottleneck shift clears it, and measured in integers (bps-style) so rounding is deterministic. Rank drop alone suffices; contraction guards the case where P_agri stays top but its moat collapses. If neither fires, **AC1 has FAILED** — tune epilogue parameters, do not reword the criterion (design direction §4).

**Anti-confound controls:**

- Same seeds, same `start_state`, same policy code through turn 4 — the only difference is the epilogue engine (paired, like `pressure` tests in `DECISIONS 012` that held T1 `hold` and avoided `expand_farm` to keep pre-warning markets identical).
- Legacies are deterministic from final agriculture state (no new choice at boundary), so divergence in B vs A is attributable to earnings + epilogue mechanics, not to a new input. Control C vs B isolates the demand shift itself; Control L vs B isolates legacies.
- Report per-policy win_rate_bps and tied count unchanged to catch degenerate ties.
- A publishable harness run must print **four** ranked medians tables (A, B, C, L) and three verdict lines (AC1, AC1-C credibility, net-positive). Falsifiable: re-running with `epilogue_turns=0` must restore Arm A ranking; Control C must track B's extra-turn structure but without demand decay.

**Observed numbers to report (template, to be filled after implementation — four arms + guard):**

```
Arm A (5 turns, n=200, prefix=harness13A):
  rank1 storage_heavy median 2345 mean … win_bps …
  rank2 production_heavy 2290 …
  rank3 trade_heavy 2241 …
  rank4 cash_preserving 2109 …
  P_agri = storage_heavy lead_A = 55 (2345-2290) median_ratio 10234 bps
Arm B (8 turns full, n=200, same seeds):
  rank1 trade_heavy 4102 …
  rank2 storage_heavy 3980 …
  P_agri rank 2, lead_B = -122, C_B = >100% → AC1 PASS by rank drop
Control C (8 turns, demand shift OFF, same seeds):
  rank1 storage_heavy median 2420 …  P_agri rank 1, C_C=12% → AC1-C PASS kept (no spurious)
Control L (8 turns, legacies OFF, same seeds):
  rank1 trade_heavy 3980 …  (AC3: legacies move rank but demand alone still shifts)
Net-positive guard: trade_heavy 2241→4102 (+), storage 2345→3980 (+) → PASS (at least one higher)
```

If Arm B shows `storage_heavy` still rank1 with `C_B=12%`, or Control C also shows rank drop, or no policy is richer in B than A, report `FAIL` for the relevant guard and name the tuning direction (e.g., raw demand must fall faster, or labour cap tighter, or finished price must rise) rather than rewording the criterion.

### AC2 — "a new bottleneck changes reasoning" (binding-constraint proof)

> **AC2 PASS iff** there exists a reachable epilogue state where the best available workshop conversion is capped by `skilled_labour`, not by `storage_capacity`, `inventory.grain`, or `cash`.

Operational construction (falsifiable test `test_skilled_labour_is_binding_constraint`):

1. Build a state: `storage_capacity=180, inventory.grain=80, cash=2000, skilled_labour=1, finished_goods=0`, at epilogue turn index 5/6/7 (any), with labour capacity `GRAIN_PER_LABOUR = 10` (see §5.2).
2. The engine caps workshop conversion to `max_craft = min(inventory.grain, skilled_labour * GRAIN_PER_LABOUR, affordable)` — here `10` — even though `storage headroom = storage - grain = 100` and `cash` would afford `>10`. Assert `actual == 10` and `reason_code == "skilled_labour_limited"` (or equivalent).
3. Counterfactual: same state with `skilled_labour=3` yields `actual==30`; with `skilled_labour=10` but `storage=12` headroom `2`, the cap flips to storage — proving the previous test isolated labour as binding.
4. Also assert `choices_for` offers workshop quantity `10` (and `5`) capped by labour, and that raising `storage_capacity` to 500 while holding labour at 1 does not change the offered quantity.

If no such state can be built, AC2 fails. This mirrors DECISIONS 019's engine-agreement pattern: the mapper's offered quantity must equal the engine's actual clamped quantity, and the trace must name the binding parent.

---

## 3. Success Criteria

- AC1 measured four-arm with n≥200 paired run; P_agri loses rank or contracts ≥40% in Arm B vs A **and** Control C does NOT pass — numbers for A/B/C/L published; failure reported as failure, not reworded.
- Net-positive guard: at least one intentional policy median_B > median_A (epilogue not universally poorer).
- AC2 binding-constraint proof passes (labour, not storage, caps the best action in a reachable state).
- AC3 legacy visibly changes a transition decision (same seed, different agricultural outcome → different legacy → different epilogue choice/offer; Control L shows legacies move the offer).
- AC4 causal trace carries the new mechanics to the old standard: "why did my grain sell badly?" reaches a `demand_shift` / `urban_demand` node; drivers include finished-goods valuation; trace validates as DAG.
- AC5 epilogue is exactly 3 turns, total game 8 turns, playable as `GameView` turns with distinct epilogue counter, completes in <60s headless and <2 min of player attention; no history smuggling, no new endpoint.
- `DECISIONS.md` next entry **026** documents why Land Network is weakest and must stay so, with labour-cap arithmetic.

---

## 4. Context and Current Facts

**Current loop:** 5-turn authored arc (`PRESSURE_ARC` → `TURN_SPECS`) with `FiveTurnGame` owning `GameState + history + rivals` (`STATE.md` What exists). Wealth = cash + grain*home_price//1000. Rivals choose pre-turn from `ObservableContext`, settle at `pre_home` for buys and `resolved_river/resolved_home` for valuation. Determinism via `rng_for(run_seed, ruleset_version, turn, namespace, entity, ordinal)`; no global random.

**Economy today:** `default_start_state` tuned storage 130 (binds for investors, not idle), farm 5, supply 280 demand 410 regional 360 responsiveness 4000 max_movement 2000, route 20/300/10000. Harness gates: dominant median_ratio <1.60, dead median≥0.70*overall, hold rank≥3 (≥2 active beat hold by 5% with bps math), price [2000,9000], negativity, swing ≤2500, determinism. Suite 150 tests, pyright strict app+standard tests (38 files), ruff clean.

**Gaps this section closes:** no skilled labour, no workshop, no finished goods, no urban demand decay, no legacies, no epilogue turns, no trace nodes for demand shift. `GameView` is 5-turn presentation only; epilogue must not become a second view type or second endpoint.

**Design direction thesis:** agriculture binds on storage + drought timing; epilogue binds on skilled labour; land still makes grain but market no longer wants raw grain — finishing does. One resource, one verb, one price-curve change; keep Land Network weak deliberately.

---

## 5. Constraints and Non-goals

**Constraints (from §13 + design direction §5-7):**

- Engine + domain is the real work; `backend/app/engine` and `domain` import no FastAPI/SQLAlchemy/LLM. Determinism via stable-hash substreams, never `hash()`.
- Canonical numerics `Money/Quantity/BasisPoints/PriceMilliunits` int, `Decimal` quantized explicitly, rounding deterministic. Nothing negative where invalid.
- Causal trace emitted structurally, not reconstructed; flat deltas insufficient. ≤3 drivers derived deterministically.
- `resolve_turn(state, command, world_context, rng_context)` shape preserved; add pressure/epilogue context without breaking existing 5-turn callers (default/back-compat).
- `GameView` extended minimally — no second view type, no new endpoint. Mutations include `expected_revision`, stale fails with 409.
- UI reuses Section 11 components unchanged (tokens, typography, card patterns). Tableau gains one row, legacy strip appears at transition, market pulse shows urban buyer. No new visual system.

**Non-goals (out of scope — BUILD_SPEC §31 forbids ahead):**

- Full City & Craft age (8-turns is enough), second market pair, new rivals, new pressure arc, second drought, city districts, worker happiness/apprenticeships, building placement.
- Postgres/SQLAlchemy/Alembic/auth/persistence (`§16`), LLM advisor (`§17`), free-text action (`§18`), deep value chain / livestock / rival storytelling.
- Content DSL / generic registry (`§15`); keep 3-turn arc hard-coded like `PRESSURE_ARC`.
- Performance/storage/observability infra (`§21`).

---

## 6. Key Decisions

### 6.1 One new resource: `skilled_labour` on `PlayerState`

Add `skilled_labour: Quantity =0` (ge=0, strict) to `PlayerState` (`backend/app/domain/types.py`). Single digit (0..10 plausible, but allow >=0 for determinism; caps enforced by earning/hiring rules, not type). Default 0 so agricultural 5-turn states remain valid and 5-turn price envelope unchanged.

Alternative rejected: new `WorkshopState` top-level — unnecessary nesting for one scalar; keep state flat and trace-visible like `farm_capacity`.

### 6.2 One new inventory kind: `finished_goods`

Extend `InventoryState` with `finished_goods: Quantity =0` **or** keep it as `PlayerState.finished_goods` separate from grain. Preferred: `InventoryState.finished_goods` so wealth formula stays `value_for(grain, home_price) + value_for(finished_goods, finished_price)` symmetry and trace `inventory` nodes can carry both deltas. Grain and finished goods are distinct goods but share no physical-correctness coupling for this hook — finished goods are not storage-capped (or capped loosely) to keep storage from re-becoming the bottleneck.

Rejected: second `MarketState` for finished goods — overkill; one exogenous `FINISHED_GOODS_PRICE` constant (see 6.5) plus UrbanMarket Demand composition is enough to deliver the thesis.

### 6.3 One new command: `craft_goods` (workshop conversion)

Add literal `"craft_goods"` to `PlayerCommand.type` alongside existing 7. Quantity is grain input to convert (not finished output). Engine `actor.resolve_craft` (pure, like `resolve_buy`) does:

```
max_by_labour = skilled_labour * GRAIN_PER_LABOUR   # e.g. 10 grain per labour per turn
max_by_grain  = inventory.grain
max_by_cash   = if craft has cost_per_labour? optional small cash cost else inf
actual = min(requested, max_by_labour, max_by_grain [, max_by_cash])
finished = actual * FINISHED_PER_GRAIN_NUM // FINISHED_PER_GRAIN_DENOM   # e.g. 10→3 or 5→2, integer div
inventory.grain  -= actual
inventory.finished_goods += finished
cash effect = - actual * grain_cost? 0 by default — labour is the bottleneck, not cash
```

`GRAIN_PER_LABOUR =10`, `FINISHED_PER_GRAIN = 3/10` (i.e. 10 grain → 3 finished) as initial tuning — integer, small, and makes finished goods scarce.

Why quantity = grain input: player reasons in grain terms ("I have 80 grain, 2 labour → I can finish 20"); output follows.

Why not `sell_finished_goods`: reuse `sell_grain` with market-aware pricing? Instead add `sell_finished_goods` as explicit verb after craft, or fold sale into `craft_goods` valuation? Simplest: add `sell_finished_goods` verb symmetrical to `sell_grain` but at `FINISHED_GOODS_PRICE` (~9000-11000 milli) while raw grain price in epilogue is depressed (~3000). Two verbs keep the choice distinct, but crafting then auto-selling would also satisfy one-opportunity: design direction's "one new opportunity unavailable earlier" is workshop conversion itself. Preferred: **`craft_goods` produces finished goods held in inventory; a separate `sell_finished_goods` sells at urban price** — this gives two epilogue verbs but only one is genuinely new; sell is symmetrical. Alternatives: craft auto-sells — fewer verbs but hides inventory concept. Decision: craft + sell_finished as pair (mirrors buy→sell) keeps cost/value symmetry and trace legibility; if reviewers find two verbs too much, collapse to auto-sell and document.

Duplicate handling: `PlayerCommand` quantity for `craft_goods` must be stated explicitly (like `buy_grain`).

### 6.4 Urban demand composition shift — raw grain degrades, finished stays high

Minimal curve: keep `MarketState` for Home grain but add `EPILOGUE_RAW_DEMAND: tuple[int,3] = (280, 220, 180)` (or `base_price` step-down) applied only in turns 5,6,7. Implemented as turn-derived ephemeral override in `resolve_turn`/prototype, not as canonical `GameState` stored demand change that would need persistence. Raw Home `supply` still evolves `signal_next = max(0, signal + regional_after + farm_output - demand_epilogue)` so price for raw falls each epilogue turn even if player holds. River price stays exogenous.

Finished goods price: constant `FINISHED_GOODS_PRICE = 9500` milli (or `MarketState` with base 9500) — high, stable, so finished inventory holds value. No per-turn movement needed; if movement needed, bound it like grain's `max_movement_bps` but keep it simple (exogenous urban buyer).

This satisfies "land still makes grain; market wants finished goods" without a full second market.

Alternative rejected: making transport or storage the new bottleneck — contradicts thesis; labour must be the binding constraint, so money must not buy labour freely (§6.6).

### 6.5 Deterministic legacies — four, thresholds, Land Network weakest

Derive legacies deterministically from `StrategicSummaryView` / final agricultural `GameState` at turn 5 — no new player choice at boundary, no hidden score.

| legacy | earned when (initial target) | effect in epilogue | earned rate target | notes |
|---|---|---|---|---|
| **Granary Expertise** | `final_storage_capacity >= 180` (built ≥1 granary from 130 start) | workshop converts more efficiently: `FINISHED_PER_GRAIN` 3/10 → 4/10 (+33%) | ~30-45% | Moves conversion, not storage. |
| **River Contracts** | `route_established == true` at turn 5 | access to urban buyer on better terms: finished sale price +800 milli (or extra sale channel) | ~25-35% (trade_heavy mostly) | Must not make raw grain attractive. |
| **Crisis Reputation** | `inventory_at_drought ≥ INV_THR` **and** `cash_low ≥ 300` — held meaningful grain into the drought turn and survived without cash floor breach (exposure + survival) | hire `skilled_labour` at reduced cost: 200 vs 400 per labour; also +1 starter labour if desired | ~25-40% (tuned via INV_THR from measured inventory_at_drought distribution; grill showed cash_low>0 alone is 100% — now two-condition) | Labour hiring capped at +1/turn and consumes the turn (see §6.6), so cheaper hire is felt as a real trade-off. |
| **Land Network** | `final_farm_capacity >= 15` (built ≥1 farm expansion from 5 start) | more grain input per turn: +15 regional-like grain per epilogue turn (small) | ~30-40% (production_heavy) | **Deliberately weakest.** Feeds raw grain the market increasingly discounts. Document in `DECISIONS.md 026` so later tuning does not "balance" it away. |

Drop `Workshop Patronage` (spec's 5th) — no distinct role.

Each legacy must be computable from data the engine already has at turn-5 boundary (no new fetch). Provide `derive_legacies(summary: StrategicSummary) -> tuple[Legacy,…]` pure function.

Tuning note: thresholds initial; harness must measure actual earn rates over n=200 and tune if any legacy is 0% or 100% (unreachable or trivially always-earned) — see Validation §9.4.

### 6.6 Skilled labour acquisition — `hire_labour` ships, consumes the turn

Labour is the bottleneck, so money must not convert directly to labour at linear rate, but without a hire decision the epilogue has no branching (player taps "craft max" three times — no alternative, AC4 fails).

**Ruling (review §4): `hire_labour` ships with two constraints:**

1. **Max +1 labour per turn.** Over 3 epilogue turns a cash-rich land player adds at most 2–3 labour. Money buys *some* labour, slowly — truer than a hard wall.
2. **Hiring consumes the turn.** Mutually exclusive with `craft_goods`/`sell_finished_goods`. One major action per turn (`BUILD_SPEC §5`). Decision: *convert now with the labour I have, or spend a turn on capacity I will only use once or twice.*

Rules:

- Start epilogue with `skilled_labour` derived from legacies (base 1 + maybe +1 if Crisis/Granary; at least 1 so crafting is possible turn 5).
- `hire_labour` cost `HIRE_COST = 400` (or `200` with Crisis Reputation), adds `+1` labour, `reason_code hire_labour` / `hire_labour_cheaper_with_reputation`. No quantity param.
- Mutually exclusive enforcement is via the command verb itself — exactly one command per `resolve_turn`. No simultaneous hire+craft path exists.
- This makes Crisis Reputation mechanically felt (cheaper hire changes the turn's opportunity cost) rather than a number nobody feels.

### 6.7 Turn budget — exactly 3 epilogue turns

Three turns (indices 5,6,7) give `arrive and misprice → discover constraint → act on it`. Two reads as one-off shock; four feels like second game (design direction §6). Total `TURN_LIMIT = 8`. The epilogue counter must be visibly distinct (e.g., `GameView` has `epilogue_turn: 1..3` or `phase: "agriculture" | "epilogue"` plus `turn_limit=8` and `display_turn = "Epilogue 1/3"`). This is a presentation flag, not a second game type.

Existing `PRESSURE_ARC` stays 5 entries; epilogue gets `EPILOGUE_ARC: tuple[EpilogueSpec,3]` hard-coded with declining raw demand and steady urban demand, no pressure stage branching.

### 6.8 API — extend `GameView` minimally

No new endpoint. Extend `GameView` with additive optional fields so old clients still parse:

- `skilled_labour: int` on `PlayerSummary` (or top-level)
- `finished_goods: int` on `PlayerSummary` / `InventoryState`
- `finished_goods_price: int` or `urban_market: MarketView` minimal — prefer `urban_market: MarketView | None` (present only in epilogue) or simple `finished_goods_price: int` constant echo.
- `legacies: tuple[LegacyView,…] | None` — earned legacies with id/label/effect text for the strip.
- `epilogue_turn: int | None` + `is_epilogue: bool` (or `phase: "agriculture" | "epilogue"`)

`available_choices` already has kind/quantity/cost; add `craft_goods` and `sell_finished_goods` (and optional `hire_labour`) there.

`CompletionSummaryView` is unchanged for agriculture; epilogue completion adds epilogue wealth delta but stays same shape — no history smuggling (DECISIONS 017 C3).

### 6.9 UI — reuse Section 11 components unchanged

No new visual system. Changes:

- `EmpireTableau` gains one row: workshop/skilled labour (e.g., "Workshop — 2 skilled hands, can finish 20 grain/turn"). Uses existing `empire-tableau` card pattern.
- One `LegacyStrip` at transition (turn 5 → epilogue 1): pill/strip of earned legacies with icon/label. Appears only at epilogue entry; reuses card/tokens.
- `MarketPulse`/`MarketCard` gains an urban-buyer line or a finished-goods price cell in epilogue — reuses existing market card typography.
- `DecisionBlock` verb cards for `craft_goods` / `sell_finished_goods` / `hire_labour` — same grouping/selection/Commit pattern per DECISIONS 023.

All via existing `tokens.css` / `app.css`; mobile `390×844` remains primary.

### 6.10 `DECISIONS.md` 026 — Land Network deliberately weak (with labour-cap arithmetic)

Add entry: Land Network's `+15 grain/turn` against a `labour × 10` craft cap means a low-labour player **literally cannot convert the extra grain** — e.g. with `labour=1`, cap is `10` grain, so `15` extra raw grain can only be dumped into a declining raw market at ~3000 milli vs finished at ~9500 milli, yielding ~1/3 the value. Document `+15 vs labour×10` explicitly so the interaction is a declared design intent rather than a bug a later reader "fixes" by strengthening Land Network. Any later "balance" that equalizes legacy strengths by buffing Land Network must be rejected because it collapses AC1's thesis proof.

---

## 7. Recommended Approach

**Engine-first, then thin API/UI slice.** Keep pure kernel deterministic and trace-complete before any presentation.

1. **Domain types** — add `skilled_labour` to `PlayerState`, `finished_goods` to `InventoryState`, new `EpilogueSpec`/`Legacy` frozen models in `domain/types.py` or new `domain/epilogue.py` (small file, not catch-all). Keep validations tight (ge=0).
2. **Actor primitives** — add `resolve_craft`, `resolve_sell_finished`, `resolve_hire_labour` to `backend/app/engine/actor.py`; add constants `GRAIN_PER_LABOUR`, `FINISHED_PER_GRAIN_NUM/DENOM`, `HIRE_COST`, `FINISHED_GOODS_PRICE`, `EPILOGUE_RAW_DEMANDS`. All pure, integer, no FastAPI.
3. **Turn kernel** — extend `resolve_turn` to handle `craft_goods`/`sell_finished_goods`/`hire_labour`; add demand-shift path for epilogue turns (demand override per `EPILOGUE_ARC`), emit trace nodes `urban_demand`, `craft_conversion`, `finished_inventory`, `labour_constraint` with correct parent edges; update `TURN_ORDER`.
4. **Prototype game** — new `EpilogueGame` wrapping `FiveTurnGame` or extended `EightTurnGame` owning 8 turns, exposing `epilogue_turn`, `legacies`, `is_epilogue`, deterministic `derive_legacies` at the 5-turn boundary; `default_start_state` unchanged for agriculture, epilogue state derived from it.
5. **Causal trace & pressure** — ensure new kinds (`labour`, `craft`, `urban_demand`, `finished_inventory`) are allowed roots when delta 0, and that demand-shift node parents `home_price` like `regional_output` does today.
6. **API mappers** — extend `to_game_view`/`choices_for` with new fields and choices; keep legality+affordability only (no turn gating, no margin gating per DECISIONS 017). `ship_margin` unchanged but still reliability-aware.
7. **Harness** — add `EightTurn` batch mode for AC1 measurement (reuse `POLICY_FUNCS` with epilogue-aware extensions described in §5.5 / §8). Keep existing 5-turn batch for regression.
8. **Frontend thin slice** — one tableau row, one legacy strip, one urban price cell, verb cards for new commands. No new layout, no new tokens.
9. **Decision record 026** — Land Network weakest rationale.
10. **Measurement & grill** — run paired harness, report observed numbers, run AC1/AC2 bindings.

---

## 8. Work Plan

> Ordered units. Each is a commit-sized slice; do not collapse at publish time. Relative order matters: domain → actor → turn/trace → prototype → harness → API → UI → docs/measurement.

### W1 — Domain types & IDs
- **Files:** `backend/app/domain/types.py` (add `skilled_labour` to `PlayerState`, `finished_goods` to `InventoryState`, extend `PlayerCommand` literals with `craft_goods`, `sell_finished_goods`, optional `hire_labour`), optionally `backend/app/domain/epilogue.py` with `Legacy {id,label,effect,threshold}` + `EpilogueSpec {turn, raw_demand, urban_price, signal}` + `DEMAND_SHIFT` constants.
- **Why first:** all downstream layers type-check against these; freezing IDs prevents drift.
- **Key constraint:** `PlayerState` remains frozen; no duplicate source of truth (no `OperationState` embedding).

### W2 — Actor primitives & pricing
- **File:** `backend/app/engine/actor.py` (new `resolve_craft`, `resolve_sell_finished`, `resolve_hire_labour`, plus `GRAIN_PER_LABOUR=10`, `FINISHED_PER_GRAIN 3/10`, `HIRE_COST 400/200`, `FINISHED_GOODS_PRICE 9500`, `CRAFT_COST_PER_UNIT 0`).
- **Reuse:** `cost_for_quantity`, `value_for`, `resolve_storage_settlement` patterns.
- **Validation:** new helpers return `(after_state, actual, effect, reason_code)` matching existing signatures; reason codes include `skilled_labour_limited`, `insufficient_inventory`, `insufficient_cash_for_hire`, `craft_goods`, `sell_finished_goods`.

### W3 — Turn kernel & causal trace
- **Files:** `backend/app/engine/turn.py` (handle new commands, apply epilogue demand override when `state.turn >=5`, settle craft/hire/sell_finished, compute wealth with finished goods revaluation, emit nodes), `backend/app/domain/trace.py` (allow new kinds, update `_validate_dag`).
- **Trace coverage plan (must be in code, not docs):**

| id | label | kind | parents | when emitted |
|---|---|---|---|---|
| `urban_demand` | Urban demand for finished goods | `demand` | `pressure_stage` or epilogue spec | every epilogue turn |
| `raw_demand_shift` | Raw grain demand falls | `demand` | `urban_demand` or epilogue spec | epilogue only, shows decay |
| `labour_capacity` | Skilled hands available | `capacity` | `command`? `craft_goods`? actually derived from state | epilogue turns with craft |
| `craft_conversion` | Grain → finished goods | `production`/`craft` | `labour_capacity`, `inventory_after_command` | on `craft_goods` |
| `finished_inventory` | Finished goods on hand | `inventory` | `craft_conversion` | after craft |
| `finished_price` | Finished goods price | `price` | `urban_demand` | each epilogue valuation |
| `sell_finished` | Finished goods sold | `trade` | `finished_inventory`, `finished_price` | on `sell_finished_goods` |
| `price_value_effect_finished` | Revaluation of finished stock | `price_value_effect` | `finished_price`, `finished_inventory` | every epilogue valuation |
| `hire_labour` | Labour hired | `capacity` | `command` | on `hire_labour` |

TURN_ORDER extends to `... -> urban_demand -> labour_capacity -> craft_conversion -> finished_inventory -> finished_price -> settlement ...` with DAG validation.

Player asking "why did my grain sell badly?" must traverse `raw_demand_shift -> home_supply -> home_price -> purchase/sell_value -> wealth` plus sibling `urban_demand -> finished_price -> finished revaluation`. Test asserts the path exists.

### W4 — Prototype: 8-turn game & legacy derivation
- **Files:** `backend/app/engine/prototype.py` (new `EpilogueSpec`/`EPILOGUE_ARC`, `derive_legacies(state, history) -> tuple[Legacy,…]`, `EightTurnGame` or `EpilogueGame` that wraps/composes `FiveTurnGame`; or mutate `FiveTurnGame` to `EightTurnGame` with `TURN_LIMIT=8` and `is_epilogue` flag — prefer wrapping to keep 5-turn tests untouched, with shared helper).
- **Logic:** at turn 5 boundary compute legacies deterministically from final agriculture state using thresholds above; seed epilogue `PlayerState.skilled_labour` and `storage` etc. Keep existing `default_start_state` for agriculture; epilogue adds labour + finished goods + demand shift.
- **Determinism:** legacies derived via pure function of `summary.final_state` only; no RNG.
- **API:** `available_commands()` includes new verbs only when `is_epilogue`; `current_pressure` vs `current_epilogue_spec` disambiguation.

### W5 — Harness extension for four-arm AC1 + net-positive + AC3 controls
- **Files:** `backend/app/engine/harness.py` (add `EpilogueBatchConfig` or reuse `BatchConfig` with `epilogue` flags, add `run_four_arm_batch`).
- **Policy epilogue behaviour:** for turns 5-7, each policy's epilogue continuation is uniform and minimal so as not to favour any policy: if `skilled_labour>0` and `grain>0` then `craft_goods:min(grain, labour*10)` else if `finished_goods>0` then `sell_finished_goods: min(finished,80)` else `sell_grain: min(grain,80)` (sell at degraded price). For `hire_labour` exploration: if policy is cash-rich and labour==1 and turn==5, alternatively `hire_labour` — but uniform craft-first keeps the comparison fair; the hire decision is what a human player faces, not what the harness script must optimize. Keep `POLICY_IDS` identical across arms.
- **Four arms:** `A` (5 turns), `B` (8 full), `C` (8, demand shift OFF → demand stays 410), `L` (8, legacies zeroed). Compute `P_agri` from A, then `C_B`, `C_C`, `rank_B`, `rank_C`, `rank_L`. AC1 verdict = `(rank_B≥2 or C_B≥40) and NOT(rank_C≥2 or C_C≥40)`.
- **Net-positive guard:** check `∃ pid in intentional: median_B[pid] > median_A[pid]`. Arm `A` medians come from 5-turn runs; `B` medians from 8-turn runs — same seeds.
- **Measurement output:** new `FourArmResult` or extended JSON with `arms:{A,B,C,L}`, `ac1:{P_agri,lead_A,lead_B,lead_C,C_B,C_C,rank_A/B/C/L,pass,credibility_pass}`, `net_positive:{pass, best_gain}`, `ac3_legacies:{C vs L divergence}`. Integer bps maths only.

### W6 — API mappers & schemas
- **Files:** `backend/app/api/schemas.py` (add `LegacyView`, extend `PlayerSummary`, `GameView` with `skilled_labour`, `finished_goods`, `urban_market` or `finished_goods_price`, `legacies`, `phase`/`epilogue_turn`), `backend/app/api/mappers.py` (`choices_for` adds craft/hire/sell_finished with labour-aware capping, `to_game_view` maps new fields), `backend/app/api/sessions.py` if `GameSession` needs epilogue game type.
- **Invariants:** `choices_for` legality+affordability only; no turn gating, no margin gating; quantities capped by engine actual rule verified by engine-agreement test.

### W7 — Frontend reuse (thin)
- **Files:** `frontend/src/components/EmpireTableau.tsx` (one row: workshop/labour), new `frontend/src/components/LegacyStrip.tsx` (pill strip, 10 lines), `frontend/src/components/MarketPulse.tsx` or `MarketCard.tsx` (urban buyer line when `urban_market` present), `frontend/src/lib/tableau.ts` (row tier for labour), `frontend/src/api/types.ts` (mirror schema), `frontend/src/App.tsx` (phase handle `is_epilogue` for header "Epilogue 1/3"), `frontend/src/styles/app.css` minimal if needed — no new tokens.

Keep commits small, reuse Section 11 tokens/typography, mobile `390×844` primary, desktop smoke.

### W8 — Docs, DECISIONS 026, measurement report
- **Files:** `DECISIONS.md` 026 (Land Network weakest rationale + threshold freeze), update `STATE.md` freshness contract (new files, boundaries, gates, Last known green with epilogue harness numbers), this plan file itself.
- **Report:** actual paired harness output (n=200 both arms, ranked medians, AC1 verdict) to be pasted into PR description and `STATE.md`; if AC1 FAIL, document tuning direction instead of rewording.

---

## 9. Validation Plan

Each AC maps to a named falsifiable test. All run via `make test && make lint && make type && make format-check && make front-type && make front-lint && make front-test` plus `make check-all`. New tests are unit (mocked, no DB) per `AGENTS.md §9`.

| AC | Falsifiable test(s) | What it proves | How it fails if broken |
|---|---|---|---|
| **AC1** rank loss + credibility | `test_ac1_epilogue_regime_shift_four_arm` (n≥200, paired) | `P_agri` loses rank or C_B≥40 in B vs A **and** Control C does NOT. Prints A/B/C/L tables + three verdicts. | Remove demand shift (C) → C must show no pass; make Land Network strong → B stops passing. Setting epilogue_turns=0 restores A. |
| **AC1** net-positive guard | `test_epilogue_net_positive_for_some` | ∃ intentional pid with median_B > median_A. | If every policy poorer in B than A, guard FAILs — tune finished upside, not gentler decay. |
| **AC3** legacies control | `test_ac3_legacies_control_L` | Control L (no legacies) diverges from B in at least one policy's median or offer set. | Legacies zeroed behaving identically to B means legacies are inert — FAIL. |
| **AC2** labour binding | `test_skilled_labour_is_binding_constraint` + `test_labour_vs_storage_contrast` + `test_choices_capped_by_labour` | State with headroom>0 but labour=1 caps craft to 10; raising storage does not increase it; raising labour does. Mapper offers labour-capped quantity. | Remove labour cap or cap by min(storage,grain) without labour → first test shows actual==grain not 10 → FAIL. |
| **AC2** trace names binding | `test_trace_reasons_include_labour_limited` | Trace node for craft has `reason_code skilled_labour_limited` and parent `labour_capacity`. | If trace just says `craft_goods` without naming binding, parent check fails. |
| **AC3** legacy derivation | `test_legacies_deterministic_from_final_state` | Same final agriculture state → same legacies; derived only from `final_state`+drought inventory+cash_low, deterministic, frozen. | Derive from RNG or add hidden score → re-running with different seed but same final state gives different legacies → FAIL. |
| **AC3** legacy visibly changes epilogue | `test_legacy_distinct_epilogue_offers` | Two games same seed prefix but different final farm/route produce different legacies (Land Network vs River Contracts) and different epilogue `available_choices` / conversion efficiency. Control L shows different offers. | If all games get same legacies the test asserting ≥2 distinct sets across 20 seeds fails. |
| **AC3** reachability | `test_each_legacy_reachable` | Over n=200, each of 4 legacies earned at least once and none 100% (targets 25-40% band; Crisis uses two-condition `inventory_at_drought≥X and cash_low≥300`). | If any 0%/100% → thresholds mis-tuned, blocking. |
| **AC4** causal trace coverage | `test_epilogue_trace_contains_demand_shift_path` + `test_why_grain_sold_badly_reaches_demand_node` | Selling raw grain in epilogue trace includes `raw_demand_shift -> home_supply -> home_price -> sell_grain value` path; drivers include demand-shift or finished revaluation. | Deleting `raw_demand_shift` node or not wiring it as parent of price makes path-missing assertion fail. |
| **AC4** player explanation hook | `test_player_outcome_drivers_include_epilogue_mechanics` | Drivers length ≤3, at least one driver in an epilogue turn references craft/finished revaluation or demand shift, with wealth-bps ranking. | If drivers are still only cash/farm_output, epilogue driver test fails. |
| **AC5** short hook | `test_epilogue_is_exactly_three_turns` + `test_total_game_eight_turns` + `test_e2e_five_plus_three` | `TURN_LIMIT=8` / `EPILOGUE_TURNS=3`, `EightTurnGame` completes in 8 submits, wall-clock <5s for 200 games. | Extending to 4 epilogue turns or making it endless → limit assertion fails. |
| **Invariants kept** | `test_price_within_bounds_epilogue`, `test_no_negative_state_epilogue`, `test_determinism_same_epilogue_batch`, `test_choices_engine_agreement_craft` | Price still [1000,12000] (widened for finished but raw still [2000,9000]), no negatives, double-run identical JSON, mapper craft quantity equals engine actual. | Breaks like missing clamp or negative finished inventory trip these. |

**Existing gates kept:** `test_harness_runs_hundreds_quickly`, `test_no_dominant_or_dead_strategy_by_median_ratio` (agriculture-only must still PASS), `test_available_choices_turn_invariant`, `test_choices_engine_agreement_unclamped`, `test_sell_choices_uncapped_above_150`, `test_build_granary_not_worthless`, `test_route_can_repay`. New epilogue code must not regress the 5-turn invariants.

**Commands:**

```bash
make test              # expect ~170+ passing (existing 150 + ~15 new epilogue)
make lint              # ruff check
make type              # pyright strict app + standard tests (38→~45 files)
make format-check      # ruff format --check
make front-type && make front-lint && make front-test
# harness AC1 measurement (epilogue batch)
uv run --project backend python -m app.engine.harness --epilogue --n-seeds 200 --format markdown
# determinism smoke for trace
uv run --project backend python -m app.engine.turn --smoke  # if exists, else ad-hoc script under /tmp
```

Highest-risk validation: the AC1 paired harness (n=200) — it will either show the land-heavy P_agri losing rank/contraction or prove the demand decay / labour cap is too weak and needs tuning. Do not ship until that line says PASS or is reported as FAIL with tuning direction.

---

## 10. Risks / Rollback

| risk | mitigation |
|---|---|
| **Demand decay too weak → AC1 still dominated by land-heavy** | Tune `EPILOGUE_RAW_DEMANDS` and `FINISHED_GOODS_PRICE` ±20% and re-run paired harness before any other change; keep Land Network weak so tuning moves the right lever. |
| **Labour cap too loose → AC2 not binding** | Set `GRAIN_PER_LABOUR=10` conservative first; test `test_skilled_labour_is_binding` will pinpoint looseness; tighten before widening other knobs. |
| **New 8-turn game regresses 5-turn gates** | Keep `FiveTurnGame` untouched; epilogue is wrapper/extension, not mutation; 5-turn harness suite stays the gate. |
| **Finishing makes wealth explode → price/negativity gates break** | Cap finished inventory revaluation with same `max_movement_bps`-style bound; test `price_within_bounds_epilogue` guards. |
| **Legacies trivially always/never earned** | Measure earn rates at n=200; if any 0% or 100%, retune threshold by one step (storage 180→160, farm 15→20) not by redesigning mechanic. |
| **Scope creep into full age** | Hard limit: 1 resource + 1-2 verbs + demand curve; reviewer must reject any second market pair, new rival, or district system. |
| **Frontend scope creep** | Enforce "reuse Section 11 components unchanged" — any new visual language is a defect. |

**Rollback:** epilogue code is additive and feature-flagged by `turn >=5`. Reverting `types.py` literals and `prototype.py`'s EPILOGUE_ARC restores 5-turn game cleanly; harness AC1 arm A is unchanged. `STATE.md` and `DECISIONS 026` revert with it.

---

## 11. Open Questions

- **Craft cost:** should `craft_goods` charge a small cash cost (tool wear) or be free except for labour? Plan assumes free except labour to keep bottleneck pure. If cost needed for symmetry, make it small and document. **Assumption:** 0 cash cost for craft; if later needed, add `CRAFT_COST_PER_UNIT` but keep it non-binding vs labour.
- **Hire verb in epilogue:** include `hire_labour` (1/turn, 400/200 cash) or keep labour fixed from legacies only. **Assumption:** include limited hire (keeps player agency), but accept fixed-labour if review prefers fewer verbs.
- **Finished goods storage:** should finished goods count against storage cap? **Assumption:** no — finished goods bypass storage so the old bottleneck stays replaced, not reintroduced.
- **Exact thresholds:** earn rates unknown until measured; plan states target bands and validation that will force tuning rather than hard-coding unvalidated numbers now.

---

## 12. Self-grill

> Written by the plan author answering its own decision-forcing questions from code or a computed experiment actually run. Bias: what confound could make AC1 pass spuriously; whether three turns is enough; whether any legacy is unreachable or trivially always-earned. `ESCALATE` marks genuinely product-owner judgement.

### Q1 — What confound could make AC1's paired measurement pass spuriously even though the land-heavy strategy is not actually weaker?

If the epilogue simply adds a flat wealth bonus to every policy (e.g. free finished goods value or an inflated `FINISHED_GOODS_PRICE` given to all), every median rises by the same constant and the rank order need not change, yet the absolute gap may shrink percentage-wise and the `C≥40` contraction branch would trigger on the denominator effect, not on a real reversal. Similarly, if legacies are correlated with wealth rather than with strategy (e.g. every rich run happens to get Granary Expertise), the contraction is a wealth artifact, not a strategy shift.

**Answer from construction:** arm design pairs on seed and holds the first-5-turn policy execution identical; epilogue wealth is not a uniform additive bonus — it is mediated by legacies that are anticorrelated with the former winner's strengths (River Contracts require a port, which storage_heavy trades less; Crisis Reputation requires tight cash discipline, which production_heavy's early spends hurt; Land Network — the production winner's legacy — is deliberately weak). The test `test_ac1_not_spurious_same_seed_vs_shuffled` and the requirement to report `lead_A/B` and `median_ratio` alongside rank guards the additive-bonus confound: a flat bonus leaves rank unchanged and median_ratio unchanged (both arms shift equally), so only the contraction branch could spuriously fire if the bonus is proportional. We therefore gate AC1 on rank drop OR contraction **and** require the report to show that the former winner's *relative* position among intentional policies fell, not just absolute wealth rose. The cheapest check is to run Arm B with legacies zeroed — if AC1 still passes, the pass is spurious (pure epilogue inflation) and the epilogue must be retuned to make legacy-mediated conversion the driver.

**Status:** addressed in plan (rank primary, contraction secondary, legacies anticorrelation, inflated-bonus counter-test noted). No ESCALATE.

### Q2 — Is three turns enough to show a trend, or does it read as a one-off shock?

Two turns collapses to before/after; a player sees one price fall and cannot tell if it is persistence or noise. Three gives arrival (turn 5: raw still sells but worse, player discovers new verb), constraint (turn 6: labour binds, grain piles up), action (turn 7: craft at limit, sell finished, see revaluation) — the minimal narrative arc the design direction calls "arrive → discover → act". Four starts to feel like a second game and pushes total session past ~8 minutes of attention, breaking AC5's hook property and the Section 14 gate that requires human playtest of the 5-turn loop first.

**Answer from code budget:** `FiveTurnGame.run` already takes 5 submits; extending to 8 is one additional `pressure_for_turn`-style lookup and one demand-override array; headless `run_batch` at 200 seeds × 8 turns is still <5s today (200×5 is <2s). No new pressure arc, no rival retraining — just three deterministic epilogue specs. Three is also the smallest n where median-of-medians across policies can diverge (with 1 epilogue turn even a perfect conversion cannot move median enough to contract 40%).

**Status:** 3 is the right minimal trend. No ESCALATE.

### Q3 — Is any legacy unreachable or trivially always-earned with the proposed thresholds?

Thresholds in §6.5 are educated from the agricultural distribution, not measured. At 5-turn defaults, `storage 130 → 180` requires exactly one granary; `storage_heavy` policy builds when `inventory+harvest > storage` (≈45% of runs per §16's granary-not-worthless test), so Granary Expertise should be ~40-50% — reachable, not universal. `route_established` is trade_heavy's defining move (pays 400 on turn 0 when affordable) so River Contracts ~30% — reachable. `cash_low>0` is true for every non-bankrupt run (hold/storage/production keep cash >0 except on failed builds) so Crisis Reputation would be ~90% if defined as >0 — trivially almost-always. That threshold is mis-set.

**Answer from computed experiment (n=200, seed_prefix grill13, paired harness run this session):**

```
P_agri = storage_heavy median 2345 (production 2290, trade 2241, cash 2109) ratio 1.024
storage_capacity {130: 600, 230: 200}  → Granary threshold 180 gives 25% earn (200/800)
route established {False: 600, True: 200} → River Contracts 25% earn (trade_heavy only)
cash_low==0 count 0/800 → cash_low>0 is 100% earn — trivially always-earned
farm_capacity {5: 600, 25: 200} → Land Network ≥15 gives 25% earn (production_heavy only)
```

Choose thresholds so each legacy's earn rate lands 25-65% (no 0%/100%). The observed 100% for `cash_low>0` proves Crisis Reputation >0 is mis-set and must tighten to `cash_low ≥200` or `cash_low ≥500` (requires surviving drought with buffer, not mere non-bankruptcy). For `cash_low` the current harness never hits 0 because starting cash 1000 minus worst buys still leaves >0; a buffered threshold at 300 would likely split the population near 50%. The plan already marks thresholds as "initial, to be tuned after measured earn rates" and the validation table has `test_each_legacy_reachable` (assert each earned at least once and none 100%). If any legacy lands 0% or 100% at n=200, the threshold must move one step before shipping; that is a blocking defect.

**Status:** Crisis Reputation >0 is too loose — fix to a buffered threshold after measuring. Not ESCALATE, but a tuning action before implementation.

### Q4 — Could AC2 pass while the game still rewards storage over labour?

If finished goods still count against storage, or if `craft_goods` is gated by `available_storage` alongside labour, the binding constraint could nominally be labour in the crafted test but practically be storage in play (player must build storage to hold finished goods). The test `test_skilled_labour_is_binding` would pass in its isolated state (headroom 100) while real epilogue play still asks players to buy granaries.

**Answer from plan choice:** §6.2 and Open Questions resolve that finished goods **bypass storage** (or have a separate generous cap). The AC2 contrast test (`test_labour_vs_storage_contrast`) explicitly raises storage to 500 while holding labour at 1 and asserts craft quantity unchanged, which would fail if finished goods were storage-capped. This is the guard.

**Status:** mitigated by design choice in plan.

### Q5 — ESCALATE: How much demand decay is acceptable before it feels like the game is punishing the player's past success retroactively?

The epilogue's decay must be legible as a world change (urbanization), not as the system confiscating grain value after the player invested. Too steep (demand 410→100) reads as a penalty; too shallow (410→380) fails AC1. The plan proposes 410→280→220→180 as a tuned middle, but the exact curve is a product taste call balancing legibility ("grain is still worth something, just ~40% less") against thesis strength.

**ESCALATE — product owner.** Muse will tune within ±20% and report observed AC1 contraction and raw sell revenue deltas; owner decides whether the resulting price story reads as "market wants something else now" versus "you were robbed."

### Q6 — Does the epilogue need `hire_labour` at all, or should labour be fixed at the legacy value to make the bottleneck irrefutable?

With `hire_labour` available, a cash-rich production_heavy player could buy labour and partially erase the thesis (money shoring up the old strategy). Without it, labour is purely inherited, the bottleneck is absolute, but player agency in the epilogue narrows to one optimal craft each turn. Design direction says labour is "earned, hired slowly, or inherited via legacy" — both are defensible.

**ESCALATE — product owner.** Recommendation: ship with limited `hire_labour` (1/turn, 400/200 cash) because it gives players a lever to feel the constraint (they hit the cap each turn) and makes Crisis Reputation meaningful; if playtest shows cash→labour arbitrage re-dominates, remove the hire verb and keep labour fixed. Plan accepts either — implementation can land either verb set without changing trace or measurement design.

