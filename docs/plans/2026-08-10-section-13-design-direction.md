# Section 13 — Design Direction (Claude, design authority)

> Input to the Section 13 plan. Authority: `docs/ORCHESTRATION.md` §5 — Claude owns
> game-design judgment, optimizing for the best game at the lowest MVP complexity.

---

## 1. The thesis, stated operationally

`BUILD_SPEC §13`: *"a successful old strategy begins to lose relative power as the economic
bottleneck changes."* This is the game's most distinctive long-term promise. It is also the
easiest thing in this whole build to fake — a section that merely *adds* a new mechanic while
the old strategy still wins has not delivered it.

**Name the bottleneck shift explicitly.**

| | Agricultural chapter | City & Craft epilogue |
|---|---|---|
| Binding constraint | **storage capacity + timing against the drought** | **skilled labour** |
| Winning behaviour | accumulate capacity, hold grain into scarcity, sell high | convert grain into finished goods; raw grain no longer clears at a good price |
| What money buys | more land, more granaries | *not* labour — labour is earned, hired slowly, or inherited via legacy |

The single sentence the design must earn: **land and storage still produce grain, but grain
stops being the thing the market wants.**

---

## 2. Lowest-complexity mechanic that delivers it

Resist adding a second full economy. The epilogue is a **hook**, not a game (AC5).

Minimum viable set:

1. **One new resource: `skilled_labour`** (small integer, single digit).
2. **One new operation: workshop conversion** — grain → finished goods, rate capped by
   `skilled_labour`. This is the "one new opportunity unavailable earlier".
3. **Urban demand composition shifts** — the settlement's demand for **raw grain falls** while
   demand for **finished goods** is high. Raw grain still sells; it just clears worse each turn.

That is one resource, one verb, and one price-curve change. Nothing else. No new rivals, no
second market pair, no new pressure arc.

**Explicitly rejected as complexity that does not serve the thesis:** a full craft value chain,
worker happiness, apprenticeships, building placement, a second drought, city districts.

---

## 3. Legacies — earned, deterministic, and one must bite

`BUILD_SPEC §13` requires concrete legacy advantages carried out of agriculture, with **at
least one visibly altering the epilogue**.

Derive them **deterministically from the final agricultural state** — no new player choice at
the boundary, no hidden score. Each must be computable from `CompletionSummaryView`-grade data
the engine already has:

| legacy | earned when | effect in the epilogue |
|---|---|---|
| **Granary Expertise** | `final_storage_capacity` ≥ threshold | workshop conversion is more efficient (better grain→goods rate) |
| **River Contracts** | `route_established` | access to the urban buyer at better terms — an extra sale channel |
| **Crisis Reputation** | survived the drought without `cash_low` hitting 0 | hire `skilled_labour` at reduced cost |
| **Land Network** | `final_farm_capacity` ≥ threshold | more grain input per turn — **deliberately the weakest legacy in the epilogue** |

**Land Network being weak is the point, not an oversight.** It is the direct payoff of the
strategy that dominated agriculture, and in the new regime it feeds a resource the market
increasingly does not want. That single asymmetry is what makes AC1 legible rather than
asserted. Say so in the plan and in `DECISIONS.md`, so a later reader does not "balance" it away.

Keep the legacy set to **four**. `Workshop Patronage` from the spec's example list is a fifth
with no distinct mechanical role here — drop it rather than invent one.

---

## 4. AC1 must be MEASURED, not argued

> "At least one previously strong Agricultural strategy becomes less dominant."

This is exactly the kind of criterion that gets declared true in a plan and never tested
(recurring failure pattern #3). We already own the instrument: the **Section 9 balance
harness** with its scripted policies.

**Operational pass/fail rule:**

1. Run the existing harness policies across the agricultural chapter. Record the ranking by
   median final wealth. Call the top policy `P_agri`.
2. Run the same policies across **agriculture + epilogue**. Record the ranking again.
3. **AC1 passes iff `P_agri` is no longer rank 1, or its median advantage over the field
   shrinks by a stated margin.** Pick the exact rule and the exact margin *before* running,
   and write both into the plan.

State the numbers actually observed. If `P_agri` still dominates by the same margin, **AC1 has
failed and the epilogue does not yet deliver the thesis** — tune the regime shift, do not
reword the criterion. A land-heavy policy must measurably lose ground.

Do not add a new policy invented to lose. The comparison must be over the **same** policy set
in both regimes, differing only in whether the epilogue is played.

Similarly, **AC2** ("a new bottleneck changes reasoning") needs an operational form: show that
under the epilogue the binding constraint on the best available action is `skilled_labour` and
not `storage_capacity`, for at least one reachable state — assert it, don't describe it.

---

## 5. Scope boundary — engine first, minimal UI reuse

AC4 says the player can *explain* why the new environment favours a different approach, and AC5
requires it to be experienced as a hook — so the epilogue must be **playable**, not just
simulated. That implies engine + API + some UI.

**Ruling on scope:**

- **Engine + domain:** the real work. New resource, conversion verb, urban demand curve,
  legacy derivation, causal trace coverage for all of it.
- **API:** extend the existing `GameView` shape minimally — do not invent a second view type.
  The epilogue is more turns of the same game, with new fields, not a new endpoint.
- **UI:** **reuse Section 11 components as-is.** The tableau gains a row, the market pulse
  shows the urban buyer, a legacy strip appears at the transition. **No new visual system, no
  new layout, no redesign** — Section 11's tokens, typography, and card patterns carry over
  unchanged. If the epilogue needs a genuinely new visual language, that is a later section.

The causal trace must cover the new mechanics to the same standard as the old (`BUILD_SPEC
§14` global rule): a player asking "why did my grain sell badly?" must get the demand-shift
node, not a bare number.

---

## 6. Turn budget

**Three turns.** Two is not enough to show a trend (one turn reads as a one-off shock); four
starts to feel like a second game and breaks AC5. Three gives: *arrive and misprice* →
*discover the constraint* → *act on it*.

The epilogue's turn counter must be visibly distinct from the agricultural five, so a player
knows they are in an epilogue and not in turn 6 of the same chapter.

---

## 7. What is out of scope

Sections 14+ (10–12 turn expansion, deep value chain, three rivals), a complete City & Craft
age, new pressure arcs, auth, database, LLM, deploy. `BUILD_SPEC §31` forbids building ahead —
and Section 14 is explicitly gated on the five-turn loop and this hook **testing well with
humans**, which has not happened yet (Section 12 is BLOCKED).
