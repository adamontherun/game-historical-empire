# Historical Empire — Ordered Build Specification

> **Repository role:** This file is the implementation authority for the current build.
>
> The product vision is larger than the first playable. The coding agent must read the whole document for context, but must implement **one numbered build section at a time, in order**, and must stop at the acceptance gate for that section.

---

## 0. How to Use This Specification

### 0.1 Purpose

Historical Empire is a mobile-first economic strategy / tycoon game about building a business dynasty across changing historical economic regimes.

The long-term game spans multiple eras. The near-term goal is much narrower: prove that a player can observe an economic situation, form a hypothesis, commit scarce resources, experience deterministic consequences, understand why the outcome occurred, and want to make another decision.

This specification intentionally separates:

1. **Long-term product direction** — what the finished game is trying to become.
2. **Current architecture principles** — rules we should preserve as we build.
3. **Ordered implementation sections** — what the coding agent is allowed to build now.

The coding agent must not interpret future product requirements as permission to implement future systems early.

### 0.2 Authority and precedence

When requirements conflict, use this order:

1. **The currently active numbered build section in this file**
2. **Accepted decisions recorded in `DECISIONS.md`, if present**
3. **Global rules in this file**
4. **Future sections in this file**
5. **Older product drafts or reference documents**

A future section is context, not current scope.

### 0.3 Agent execution protocol

For every numbered build section:

1. Read this entire file once for context.
2. Read the active section again carefully.
3. Inspect the existing repository and tests before proposing changes.
4. Use Muse `/plan` to produce the smallest coherent implementation plan.
5. Use `/grill` to challenge the plan for scope creep, unnecessary abstractions, missing tests, hidden assumptions, and work that belongs in a later section.
6. Revise the plan downward if possible.
7. Use `/goal` to implement only the approved section.
8. Run every acceptance check in the section.
9. Stop.
10. Report:
   - files changed
   - commands run
   - tests/checks run
   - results
   - known risks or follow-up observations

Do **not** automatically continue to the next section.

### 0.4 Section status

The agent may update only the `Status` line of a section after all acceptance criteria pass.

Allowed values:

- `NOT STARTED`
- `IN PROGRESS`
- `COMPLETE`
- `BLOCKED`

Do not silently weaken acceptance criteria to mark a section complete.

### 0.5 Default development rule

> **Full context, narrow authority.**

The agent should understand where the game is going, but only build what the current section requires.

---

# Part I — Product North Star

## 1. Product Thesis

Historical Empire is a strategy / tycoon game in which the player builds an economic dynasty across changing historical regimes.

The player is not primarily placing buildings on a map. The player is making consequential economic choices under the constraints of an era.

The core loop is:

```text
Observe
  ↓
Choose
  ↓
Commit
  ↓
Advance time
  ↓
Experience consequences
  ↓
Understand why
  ↓
Adapt
  ↓
Grow
```

The game should make the player feel two things:

> **I built an enormous economic empire.**

and:

> **Now I understand why a different strategy became powerful in a different economic environment.**

The game teaches economic intuition through consequences rather than lectures.

Concepts the player should eventually experience include:

- opportunity cost
- scarcity
- supply and demand
- surplus
- storage
- spoilage
- specialization
- trade
- transport friction
- comparative advantage
- capital
- credit
- fixed versus marginal costs
- economies of scale
- logistics
- information delay
- market saturation
- brands
- network effects
- automation
- shifting bottlenecks

The game should almost never stop to explain these as textbook concepts. The player should infer them from what happens.

---

## 2. Signature Design Rule

The most important simulation rule is:

> **Author the cause. Simulate the consequences.**

Example:

```text
Drought
  ↓
Farm output falls
  ↓
Regional grain supply falls
  ↓
Supply becomes scarce relative to demand
  ↓
Price pressure rises
  ↓
Market price moves upward
  ↓
Stored grain becomes more valuable
  ↓
Food processors face higher input costs
  ↓
Trade from other markets becomes more attractive
```

The game must not replace this with:

```text
drought => grain_price += 40%
```

Historical transitions and world pressures may be authored. Their economic effects should travel through simulation systems whenever practical.

---

## 3. The Long-Term Hook

The long-term hook is not merely “business through history.”

It is:

> **Build a dynasty by spotting the next economic bottleneck before your rivals — and knowing when yesterday's winning strategy has become obsolete.**

The player should eventually experience multiple economic regimes such as:

1. Forager
2. Agricultural
3. City & Craft
4. Merchant
5. Industrial
6. Mass Market
7. Information
8. Automation

These are design chapters, not a claim that every society followed one universal linear path.

Each major transition should change four things:

1. A previously dominant constraint becomes less important.
2. A new bottleneck becomes decisive.
3. At least one old strategy loses relative power.
4. At least one new strategic action or business model becomes possible.

Examples:

| Transition | Old advantage weakens | New bottleneck | New opportunity |
|---|---|---|---|
| Agricultural → City & Craft | raw land scale alone | skilled labor and urban access | workshops, processing, specialization |
| Merchant → Industrial | relationships and arbitrage alone | fixed capital, energy, capacity | factories and mechanization |
| Industrial → Mass Market | production scale alone | distribution and consumer attention | brands and segmentation |
| Information → Automation | cheap information processing alone | compute, energy, trust, judgment | automated production and services |

The first playable will only prove a tiny portion of this promise.

---

# Part II — Global Game Design Rules

## 4. Player Decisions, Not Spreadsheet Operations

The player should think like an entrepreneur, merchant, allocator, owner, or strategist.

Avoid requiring continuous tuning of:

- exact prices
- worker wages
- production quotas
- reorder thresholds
- dozens of individual buildings
- transport schedules
- numerical tax rates

Prefer strategic abstractions such as:

```text
Expand farmland
Build storage
Secure a trade route
Preserve cash
Borrow and scale
Specialize
Diversify
Change market posture
Acquire a distressed rival asset
```

The dashboard is the scoreboard, not the job.

---

## 5. One Meaningful Major Action per Turn

The default turn should present one meaningful allocation decision.

The player may inspect information freely, but normally commits only one major strategic action before time advances.

This creates opportunity cost.

A strong decision should satisfy most of these:

- at least two options are credible
- the best choice depends on current state
- there is a short-term versus long-term trade-off
- it affects more than one system
- it creates exposure to a future condition
- a rival may react or benefit
- the result can be explained afterward
- no option is always correct across all runs

---

## 6. Signals Before Consequences

Major disruptions should usually have some form of signal before impact.

Examples:

- unusually dry weather
- falling harvest estimates
- migration
- rising caravan activity
- political tension
- a rival accumulating inventory
- increasing demand in another settlement

The player should often be able to form a hypothesis before the consequence arrives.

Randomness should create stories, not arbitrary punishment.

A prepared player should usually be hurt less by bad luck than an unprepared player.

---

## 7. Rivals Are Strategic Signals

Rivals are not decorative scoreboards.

They should be:

- named
- visually recognizable
- strategically legible
- capable of success and failure
- present frequently
- deterministic in their economic decisions

Rival behavior should help the player infer the world.

Example:

```text
Mira has leased another grain store.
```

That is characterization and an economic signal.

Long term, LLMs may control how rivals speak. They must not determine how rivals obtain money, choose canonical investments, or alter game state.

---

## 8. Visible Compounding

The player must feel that an empire is becoming materially larger.

A business represents an economic operation, not an individually placed building.

Example:

```text
Family Plot
→ Grain Estate
→ Northern Grain Holdings
→ Regional Supplier
→ River Trade Network
```

The UI should show visible growth through names, scale indicators, illustrations, operation counts, trade reach, and outcome reveals.

---

## 9. Outcome Reveal Is a Signature Interaction

After a committed decision, time advances and the game should reveal the consequences in a satisfying sequence.

Recommended order:

1. Time advances.
2. World condition changes.
3. Player economic numbers change.
4. The largest positive and negative effects appear.
5. The causal explanation appears.
6. Rival outcomes or reactions appear.
7. The next opportunity or threat becomes visible.

Example:

```text
6 MONTHS LATER

Wealth
4,820 → 6,140

Grain inventory value
+18%

Farm income
-21%

WHY?
The northern harvest failed, reducing regional supply.
Your stored grain gained value as prices rose.

MIRA
Expanded storage before the shortage.

DARAN
Large new farmland purchases left him exposed.
```

---

# Part III — Global Technical Rules

## 10. Simulation Authority

The backend simulation is the source of truth.

Clients may send commands, never canonical state mutations.

Good:

```json
{
  "type": "build_granary",
  "operation_id": "home_estate"
}
```

Bad:

```json
{
  "cash": 999999999
}
```

The engine determines actual cost, validity, effects, and resulting state.

---

## 11. Determinism

The same initial state, same commands, same ruleset, and same seed must produce the same result.

Never use Python global random state.

Randomness must come from stable deterministic keyed substreams.

Do not derive persistent randomness from Python's built-in `hash()`.

Use canonical serialization plus a stable hash such as BLAKE2 or SHA-256 to derive random substream seeds.

Suggested key material:

```text
run_seed
ruleset_version
turn
system_namespace
entity_id
ordinal
```

Unrelated code changes should not shift all future random outcomes.

---

## 12. Canonical Numeric State

Avoid floating-point canonical economic state.

Use integer types for canonical values:

```text
Money = int
Quantity = int
BasisPoints = int
PriceMilliunits = int
```

Where:

```text
10,000 basis points = 100%
```

Transient calculations may use `Decimal` when appropriate, but must be quantized explicitly into canonical integer state.

Rounding rules must be deterministic and tested.

---

## 13. Pure Engine Boundary

The simulation engine should remain independent of:

- FastAPI
- React
- SQLAlchemy
- Clerk
- OpenRouter
- rendering libraries

Core engine functions should be testable without network, database, browser, or external services.

Preferred shape:

```python
resolve_turn(
    state,
    command,
    world_context,
    rng_context,
) -> TurnResolution
```

Where `TurnResolution` contains at least:

- `next_state`
- `domain_effects`
- `causal_trace`
- `player_outcome`

---

## 14. Causal Trace Is First-Class Output

Do not reconstruct causality later by diffing snapshots.

The engine must emit structured causal information as it resolves changes.

Example:

```json
{
  "cause": "northern_drought",
  "effects": [
    {
      "metric": "farm_output",
      "before": 100,
      "after": 68,
      "reason_code": "drought_reduced_yield"
    },
    {
      "metric": "regional_grain_supply",
      "before": 240,
      "after": 208,
      "reason_code": "lower_regional_output"
    },
    {
      "metric": "grain_price",
      "before": 5000,
      "after": 5600,
      "reason_code": "supply_below_demand"
    }
  ]
}
```

The causal trace will eventually support:

- outcome reveals
- market explanations
- advisor answers
- run history
- debugging
- balance analysis
- replay inspection

---

## 15. Keep Early Architecture Concrete

Do not design a universal mechanism merely because a future age might need it.

Create abstractions after at least two concrete use cases reveal a shared pattern.

The early game should use a small common kernel plus explicit mechanics.

Possible long-term mechanic modules include:

- seasonality
- spoilage
- transport friction
- information delay
- skill scarcity
- credit
- fixed-cost scale
- brand demand
- network effects
- intellectual property
- automation substitution
- compute and energy constraints

Do not implement these until a numbered section requires them.

---

## 16. Testing Priority

Testing priority:

```text
VERY HIGH
engine unit tests

HIGH
invariants / property tests

HIGH
headless simulation tests

MODERATE
API integration tests

LIMITED BUT IMPORTANT
critical browser-flow tests
```

Do not chase repository-wide 100% coverage.

Focus on economic invariants, determinism, action validation, causal correctness, and critical player flows.

---

# Part IV — Ordered Build Plan

---

# SECTION 1 — Repository Contract and Walking Skeleton

**Status:** COMPLETE

## Goal

Create the smallest repository structure and development contract needed to build and test a pure Python game engine.

No gameplay beyond a trivial test fixture is required.

## In scope

Create or confirm:

```text
backend/
  app/
    domain/
    engine/
  tests/

frontend/        # may remain empty or minimal if already present

docs/
```

Create baseline Python project configuration and test commands if they do not already exist.

Create `DECISIONS.md` with an initial entry stating:

- the original product vision is intentionally broader than the first playable
- this ordered specification is the current implementation authority
- future systems must not be built early without an active section requiring them

Create one trivial deterministic engine test proving the test harness works.

## Explicitly out of scope

- real economy logic
- FastAPI routes
- database
- React UI
- rivals
- content framework
- LLM integration
- authentication
- deployment

## Acceptance criteria

1. A clean checkout can install backend dependencies.
2. One command runs backend tests successfully.
3. Linting and type checking commands exist.
4. The engine package does not import web, database, or LLM packages.
5. `DECISIONS.md` records the scope strategy.
6. No future systems are scaffolded merely for completeness.

## Stop condition

Stop when the repository can run a trivial pure-engine test and all baseline checks pass.

---

# SECTION 2 — Core Economic Types and Deterministic Randomness

**Status:** COMPLETE

## Goal

Create the minimum canonical types and deterministic RNG interface needed for economic simulation.

## In scope

Define minimal typed models for:

```text
GameState
PlayerState
MarketState
OperationState
InventoryState
TurnContext
```

Only include fields needed by Sections 2–4.

Required concepts:

- player cash
- grain inventory
- farm capacity
- storage capacity
- regional grain supply
- regional grain demand
- grain price
- current turn
- run seed
- ruleset version

Add deterministic random substream generation using a stable hash.

Add fixed-point integer aliases or constrained types for:

- money
- quantity
- basis points
- price milliunits

Define explicit integer rounding helpers if any percentage arithmetic is introduced.

## Explicitly out of scope

- all eight age schemas
- generic business schema registry
- JSON content loader
- rivals
- routes
- API
- persistence
- domain event persistence

## Acceptance criteria

1. Canonical economic values are integers.
2. Invalid negative canonical state is rejected where appropriate.
3. Stable substream derivation returns the same output for the same key material.
4. Different namespaces produce different deterministic streams.
5. No use of Python global random state exists in the engine.
6. Tests cover rounding and deterministic seed derivation.

## Stop condition

Stop when the core types and deterministic RNG are stable enough to implement a one-turn grain market.

---

# SECTION 3 — One-Turn Grain Market Kernel

**Status:** COMPLETE

## Goal

Prove the smallest important economic causal chain:

```text
drought
→ lower grain production
→ lower market supply
→ increased scarcity
→ upward price pressure
→ price movement
→ changed player exposure
```

## In scope

Support one market and one good: grain.

Support player state containing:

- cash
- grain inventory
- farm capacity
- granary storage capacity

Support market state containing:

- supply
- demand
- base price
- current price
- responsiveness
- maximum per-turn movement

Support world conditions:

- normal harvest
- drought

Support player commands:

- expand farm
- build granary
- buy grain
- hold cash

The action may apply before the harvest / market resolution depending on the turn-resolution order chosen in the plan. The order must be explicit and tested.

### Market model

Use an intentionally simple and legible model.

Conceptually:

```text
imbalance = demand - supply

normalized_imbalance = imbalance / effective_supply

price_pressure = normalized_imbalance × responsiveness

target_price = base_price adjusted by price_pressure

new_price = bounded movement toward target_price
```

Do not blindly copy this formula if a simpler integer-safe equivalent produces clearer behavior. Preserve these properties:

- lower supply relative to unchanged demand creates non-negative upward price pressure
- higher supply relative to unchanged demand creates downward pressure
- prices stay positive
- extreme movements are bounded
- price changes have inspectable causes

### Drought rule

A drought must reduce production or yield.

It must **not** directly apply a price modifier.

### Opportunity cost

Commands must consume scarce resources or foreclose alternatives.

Examples:

- expanding farm consumes cash
- building storage consumes cash
- buying grain consumes cash and storage capacity
- holding cash gains no immediate productive asset

## Required outputs

`resolve_turn` should return:

- next canonical state
- domain effects
- causal trace
- concise player outcome

## Acceptance criteria

1. Same state + command + world condition + seed = identical result.
2. Reducing supply with demand unchanged cannot reduce target price.
3. Drought influences price through production and supply, not a direct price mutation.
4. Cash, inventory, capacity, supply, demand, and prices cannot become negative.
5. Buying beyond cash or storage is rejected or safely bounded according to one explicit rule.
6. Every major displayed economic change has a corresponding causal-trace entry.
7. A CLI demo prints before state, command, world condition, causal chain, and after state.
8. Unit tests and invariant tests pass.

## Stop condition

Stop when one economic turn is deterministic, explainable, and testable.

---

# SECTION 4 — Causal Explanation and Outcome Model

**Status:** COMPLETE

## Goal

Make economic resolution legible enough that a player-facing interface can later explain what happened without reconstructing causes.

## In scope

Formalize:

```text
DomainEffect
CausalNode
CausalEdge or parent reference
CausalTrace
PlayerOutcome
OutcomeDriver
```

The exact representation may differ, but it must support a causal chain rather than a flat list of unrelated deltas.

Support ranking of the top player-facing drivers.

A turn should generally show no more than three primary causal drivers in the main reveal, while preserving the full debug trace internally.

Example:

```text
1. Drought reduced your farm output by 32%.
2. Regional grain supply fell below demand, pushing price upward.
3. Your stored grain gained value, partially offsetting lower farm income.
```

## Explicitly out of scope

- LLM narration
- advisor chat
- natural-language action interpretation
- persistence

## Acceptance criteria

1. Every important state change can be traced to at least one parent cause.
2. Player-facing drivers are derived from engine trace data, not snapshot guessing.
3. Driver ranking is deterministic.
4. The CLI demo can show both concise explanation and full debug trace.
5. Tests cover at least one multi-step chain from drought to player wealth effect.

## Stop condition

Stop when the engine can answer “why did this happen?” structurally without any LLM.

---

# SECTION 5 — Two Markets and One Trade Route

**Status:** COMPLETE

## Goal

Add meaningful spatial economics without adding a geographic map.

## In scope

Add two named market nodes:

### Home Valley

Characteristics:

- agricultural production center
- relatively high grain supply after harvest
- more exposed to local weather

### River Town

Characteristics:

- growing population
- stronger food demand
- higher potential grain price during shortages
- source of future craft specialization

Add one route:

### River Route

Required properties:

- transport cost
- carrying capacity
- reliability
- optional travel or settlement delay if useful
- event exposure

Support a player command or operation that creates trade access.

The player does not place anything on a map.

The UI representation later will be cards / nodes / route status, not free spatial placement.

## Optional mechanic

If implementation remains simple, allow River Town market information to be stale by one turn until the player has reliable trade access.

Do not implement this optional mechanic if it expands the section substantially.

## Acceptance criteria

1. Home Valley and River Town can have different prices from the same underlying good.
2. Transport cost can make an apparent price difference unprofitable.
3. Route capacity constrains trade volume.
4. A profitable arbitrage opportunity can emerge from market conditions rather than a scripted reward.
5. The player can remain entirely in Home Valley and still complete a turn.
6. All results remain deterministic.

## Stop condition

Stop when regional trade creates at least one genuinely different strategic choice from pure farm expansion or storage.

---

# SECTION 6 — Five-Turn Headless Prototype

**Status:** NOT STARTED

## Goal

Create the first complete playable strategy loop entirely in the terminal.

The purpose is to prove game decisions before investing in a browser interface.

## Exact prototype scope

- five turns
- grain only
- Home Valley
- River Town
- one river route
- farm expansion
- granary / storage
- trade access
- cash preservation
- one major action per turn
- deterministic world pressures
- outcome reveal text
- no database
- no LLM

## Five-turn arc

### Turn 1 — A Growing Settlement

The settlement is expanding and food demand is rising.

The player chooses an initial posture.

### Turn 2 — Surplus

A strong harvest produces abundant grain and weak prices.

Storage and trade become interesting.

### Turn 3 — Warning Signs

Dry weather and other signals suggest a potential production shock.

The player sees rivals beginning to position themselves.

### Turn 4 — Drought

The drought resolves through production, supply, prices, player exposure, and rival exposure.

### Turn 5 — Aftermath

The player responds to the new economic environment.

Possible opportunities include:

- selling inventory
- buying distressed productive assets
- expanding trade
- expanding storage
- preserving liquidity

## CLI requirements

Each turn shows:

- turn number
- current signal
- player cash
- player operations
- grain inventory
- Home Valley market pulse
- River Town market pulse
- route status
- available major actions
- result after commit
- top causal drivers

## Acceptance criteria

1. A complete run requires exactly five player decisions.
2. The game can be completed from the terminal.
3. Same seed + same choices = same final state.
4. At least three intentionally different player strategies produce meaningfully different exposures and outcomes.
5. The drought rewards preparation without guaranteeing one universally best strategy.
6. The player can understand the top causes of each turn result.
7. The run ends with a concise strategic summary.

## Stop condition

Stop when the five-turn game is playable without a browser and feels like a sequence of economic decisions rather than a simulation demo.

---

# SECTION 7 — Deterministic Rivals

**Status:** NOT STARTED

## Goal

Make the world feel competitive and strategically legible through two recurring rivals.

## Rivals

### Mira

Strategic identity:

- storage
- trade
- relationships
- flexibility
- moderate risk
- reacts to shortage signals early

### Daran

Strategic identity:

- farmland
- production scale
- aggressive expansion
- higher concentration risk
- greater vulnerability to drought and cash pressure

## In scope

Rivals may use simple deterministic scoring functions.

Conceptually:

```text
opportunity score =
expected return
× strategic preference
× available capital
× risk fit
× current exposure
```

Use seeded deterministic tie-breaking if needed.

Every turn after the first should reveal at least one visible rival action, intention, or consequence.

Examples:

```text
Mira leased additional storage.
Daran bought another large tract of farmland.
Mira secured capacity on the river route.
Daran is short of cash after expanding aggressively.
```

## Explicitly out of scope

- LLM rival decisions
- chat negotiation
- complex personality simulation
- more than two rivals

## Acceptance criteria

1. Mira and Daran make different choices from the same world state often enough to be recognizable.
2. Their choices are deterministic given state and seed.
3. Their capital constraints are real.
4. They cannot create money or assets outside the same economic rules unless explicitly modeled as starting conditions.
5. At least one rival action can change what a rational player might choose.
6. Rival outcomes are included in turn reveals.

## Stop condition

Stop when a player can identify which rival is which from behavior alone.

---

# SECTION 8 — Pressure-Driven Event Arc

**Status:** NOT STARTED

## Goal

Replace isolated random event spam with a small coherent world-pressure system.

## In scope

Implement one pressure arc:

```text
normal conditions
→ early dry signal
→ worsening dry signal
→ drought impact
→ aftermath
```

The exact turns may be authored for the first prototype.

The engine should keep the impact systemic.

Create a minimal event / world-pressure representation containing only fields the prototype needs.

Possible fields:

```text
id
stage
signal_text
world_modifiers
activation_turn
causal_source_id
```

Do not build a general 30-event weighted content framework yet.

## Acceptance criteria

1. The player receives at least one useful warning before the drought impact.
2. The drought consequence still travels through production and markets.
3. Different player preparation produces different results from the same drought.
4. The pressure arc is deterministic and inspectable.
5. The system is small enough to understand without a generic rule DSL.

## Stop condition

Stop when the five-turn story feels coherent and anticipatory rather than randomly punitive.

---

# SECTION 9 — Headless Strategy and Balance Harness

**Status:** NOT STARTED

## Goal

Detect obvious dominant strategies and broken economic ranges before building the UI.

## In scope

Create scripted player policies such as:

- production-heavy
- storage-heavy
- trade-heavy
- cash-preserving
- random legal action

Run many deterministic seeds headlessly.

Measure:

- final wealth
- cash lows
- inventory levels
- exposure to drought
- strategy win rate
- strategy median outcome
- bankrupt / near-bankrupt conditions if applicable
- price ranges
- largest single-turn wealth swing

Do not optimize for equal strategy outcomes.

The target is:

- no universally dominant strategy
- no obviously dead strategy
- bad luck is mitigated by preparation
- results remain within legible ranges

## Acceptance criteria

1. A command can simulate at least hundreds of five-turn games quickly.
2. No strategy wins across essentially every representative seed.
3. No common strategy routinely causes impossible negative state.
4. Price ranges stay within deliberate bounds.
5. Same simulation batch configuration reproduces identical aggregate results.
6. Output is easy to compare in CI or local development.

## Stop condition

Stop when the prototype is stable enough that UI playtesting is more valuable than additional headless tuning.

---

# SECTION 10 — Minimal FastAPI Boundary

**Status:** NOT STARTED

## Goal

Expose the existing game through a minimal server API while keeping the engine pure.

## In scope

Use in-memory game sessions only.

Required endpoints:

```text
POST /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/{game_id}/choices/{choice_id}
```

Create a presentation-oriented `GameView` containing what the frontend needs to make the current decision.

Suggested fields:

```text
game_id
revision
turn
turn_limit
signal
player_summary
empire_summary
home_valley_market
river_town_market
route_status
mira_headline
daran_headline
available_choices
latest_outcome
completion_summary
```

Mutating requests include an expected state revision.

A stale revision must fail.

## Explicitly out of scope

- PostgreSQL
- SQLAlchemy
- Alembic
- authentication
- LLM endpoints
- history endpoint
- cloud deployment

## Acceptance criteria

1. API tests can create and complete a five-turn game.
2. Invalid commands cannot mutate state.
3. Stale revisions cannot mutate state.
4. The frontend will not need to reproduce economic formulas.
5. Engine code imports no FastAPI modules.
6. Full backend test suite remains passing.

## Stop condition

Stop when a client can play the entire prototype through three simple in-memory endpoints.

---

# SECTION 11 — Mobile-First React Playable

**Status:** NOT STARTED

## Goal

Create the first real vertical slice the user can play in a browser on a phone-sized viewport.

## Primary flow

```text
Start game
→ read signal
→ inspect concise market/rival context
→ choose one major action
→ commit
→ see time advance
→ see outcome reveal
→ understand why
→ continue
```

## Required screen content

- age / chapter label
- turn number
- player cash
- compact empire growth indicator
- hero / world-state area using placeholders
- current signal
- current decision
- 2–4 action buttons
- Home Valley market pulse
- River Town market pulse
- route status
- Mira headline
- Daran headline
- outcome reveal
- completion summary

## UI principles

- mobile first
- approximately 390 × 844 must be excellent
- desktop remains usable
- cards, typography, visual hierarchy, and transitions over dense tables
- required decision information is visible on the main screen
- detail views are optional depth, not homework
- no multi-tab dashboard maze
- outcome reveal should feel like a payoff moment

## Empire tableau

Create a lightweight visual representation of growth.

Example:

```text
Family Farm
  ↓
Expanded Grain Estate
  ↓
Granary Network
  ↓
River Trade Access
```

Automatic layout is fine. The player does not place buildings.

## Browser verification

Use Playwright for the critical path.

Capture screenshots for:

- first decision
- drought warning turn
- drought outcome reveal
- final summary

Inspect browser console during the critical path.

## Explicitly out of scope

- authentication
- database
- LLMs
- polished art pipeline
- bottom-navigation architecture
- multiple age screens
- free-text commands

## Acceptance criteria

1. A new player can start and finish the five-turn game from a phone-sized viewport.
2. No dense table is required to make a decision.
3. Every turn result says what changed and why.
4. Rivals remain visible throughout the run.
5. The empire indicator visibly changes during the run.
6. A committed action cannot be accidentally submitted twice.
7. No browser console errors occur on the critical path.
8. Playwright completes the full five-turn flow on mobile and a desktop smoke test.

## Stop condition

Stop when the five-turn game is comfortably playable and understandable in the browser.

---

# SECTION 12 — First Human Playtest and Refinement Gate

**Status:** NOT STARTED

## Goal

Evaluate whether the core game loop is worth expanding.

This is a product milestone, not a feature milestone.

## Playtest questions

Before each player decision ask:

> What do you expect will happen, and why?

After each outcome ask:

> Why do you think that happened?

At the end ask:

> Did you want one more decision?

Observe:

- decision clarity
- consequence clarity
- strategic depth
- rival legibility
- visible empire growth
- pacing
- mobile usability
- whether the player formed and revised hypotheses

## Agent work after playtest

The coding agent receives written playtest observations.

It must classify each observation as:

- decision clarity
- consequence clarity
- strategic depth
- rival legibility
- visible empire growth
- mobile usability
- pacing
- technical defect
- deferred feature request

Then identify the three highest-impact problems.

Fix only those three.

## Explicitly forbidden during this section

Do not respond to playtest feedback by adding:

- more goods
- more turns
- more rivals
- database
- authentication
- LLMs
- new age systems
- large UI redesigns

unless one is literally required to fix a critical blocker.

## Go / no-go criteria

Proceed only when most of these are true:

1. A fresh player completes the run without developer explanation.
2. Before committing, the player can describe a plausible expected outcome.
3. After resolution, the player can explain the primary causal chain.
4. At least three strategic approaches feel defensible in some state.
5. A rival changes at least one player decision.
6. The empire feels larger at the end.
7. The drought feels consequential but not arbitrary.
8. Players disagree about the best strategy.
9. At least some players want to continue.

## Stop condition

If the core loop is not working, remain in this section and iterate on the existing systems.

Do not advance by adding features to hide a weak decision loop.

---

# SECTION 13 — City & Craft Transition Epilogue

**Status:** NOT STARTED

## Goal

Prove the game's most distinctive long-term promise: a successful old strategy begins to lose relative power as the economic bottleneck changes.

## In scope

Add a short 2–3-turn epilogue or transition chapter after the Agricultural prototype.

The transition should introduce:

- settlement growth into an urban center
- increased importance of skilled labor
- stronger value of processing / workshops
- reduced relative dominance of raw farmland ownership alone
- one new opportunity unavailable earlier

Do not build a complete City & Craft Age.

## Concrete legacy

At the end of agriculture, award one or more concrete legacy advantages such as:

- Granary Expertise
- River Contracts
- Land Network
- Workshop Patronage
- Crisis Reputation

At least one legacy must visibly alter the City & Craft epilogue.

Keep any deeper abstract scores internal if useful.

## Acceptance criteria

1. At least one previously strong Agricultural strategy becomes less dominant.
2. At least one new bottleneck changes the player's reasoning.
3. A legacy choice or earned legacy visibly changes a transition decision.
4. The player can explain why the new environment favors a different approach.
5. The epilogue remains short enough to serve as a hook, not a second full game.

## Stop condition

Stop when the player has experienced one meaningful economic regime shift.

---

# SECTION 14 — Expand Agricultural Prototype to 10–12 Turns

**Status:** NOT STARTED

## Goal

Only after the five-turn loop and regime-shift hook test well, expand the Agricultural chapter into a richer MVP session.

## In scope

Expand toward:

- 10–12 meaningful turns
- one deep grain value chain
- one alternative hedge or secondary economic path
- three rivals maximum
- several pressure arcs
- contested opportunities
- stronger empire compounding

### Preferred deep grain chain

```text
land and labor
→ grain production
→ storage and spoilage
→ milling / processing
→ local sale or regional trade
```

### Secondary path

Choose one:

- livestock
- textiles
- another clearly differentiated hedge

Do not add several shallow commodities simply to increase content count.

### Contested opportunities

Add scarce opportunities such as:

- one favorable caravan contract
- one irrigated land purchase
- one skilled workshop specialist
- one political exemption
- one reliable supplier relationship

If the player declines, a rival may take the opportunity.

## Content target

Prefer approximately:

- 8–12 strong decision situations
- 5–8 coherent event / pressure arcs or authored developments

over dozens of isolated cards.

## Acceptance criteria

1. Session length remains focused and replayable.
2. The new content introduces new trade-offs rather than duplicate decisions.
3. The value chain creates at least four recognizable strategic identities.
4. No single strategy dominates all representative seeds.
5. Rivals remain legible rather than becoming noisy.
6. The player still sees no more than a small number of primary decisions at once.

## Stop condition

Stop when additional turns increase strategic depth rather than merely session length.

---

# SECTION 15 — Content Model and Validation

**Status:** NOT STARTED

## Goal

Introduce version-controlled content definitions only after there is enough content to justify separating parameters from code.

## Principle

Python owns formulas.

Content data supplies parameters.

Never put arbitrary executable formulas in JSON.

Bad:

```json
{
  "formula": "(price * output) - labor * era_modifier"
}
```

Good:

```json
{
  "id": "wheat_farm",
  "base_output": 100,
  "weather_sensitivity_bps": 8500
}
```

## In scope

Introduce validated definitions for the content that actually exists, such as:

- goods
- operation types
- rivals
- world-pressure arcs
- decisions
- visual profile ids

Use strict Pydantic validation.

Validate cross-references.

Introduce:

```text
content_version
schema_version
```

Do not create placeholder content for all eight ages.

## Acceptance criteria

1. Existing prototype content loads from validated version-controlled data where appropriate.
2. Invalid references fail validation.
3. Duplicate ids fail validation.
4. Formulas remain in Python.
5. Content changes do not require editing simulation formulas.
6. The loader remains easy to understand.

## Stop condition

Stop when content authorship is easier without introducing a mini programming language.

---

# SECTION 16 — Persistence and Save / Resume

**Status:** NOT STARTED

## Goal

Persist completed turns and allow a run to resume after browser refresh or server restart.

## In scope

Introduce PostgreSQL only now.

Use a deliberately simple snapshot-first model.

Persist per game run:

- run id
- run seed
- ruleset version
- content version
- schema version
- current turn
- current revision
- status

Persist each completed turn with enough information for debugging and later replay:

- command
- previous revision
- deterministic random keys / consequential rolls
- emitted domain effects
- causal trace summary or reference
- post-turn snapshot
- post-turn state hash

Snapshot after every completed turn initially.

## Event sourcing position

The engine may already emit domain effects/events internally.

Do not make a complete durable event ledger the sole source of truth yet unless replay needs have clearly justified that complexity.

Snapshots are authoritative for resume in this section.

## Concurrency

Use optimistic revision checks.

A stale write returns conflict rather than silently applying to another state.

## Acceptance criteria

1. A game resumes after backend restart.
2. Reloading the browser returns the same current game state.
3. Stale revision updates fail safely.
4. Same saved seed/ruleset/commands reproduce the same turn result in a verification test.
5. Snapshot state is validated when loaded.
6. Database code remains outside the pure engine.

## Stop condition

Stop when save/resume is dependable for playtesting.

---

# SECTION 17 — Grounded Advisor

**Status:** NOT STARTED

## Goal

Add the first LLM feature only after the deterministic game is fun and its causal traces are mature.

The advisor answers questions such as:

> Why did my profits fall?

> Why did Mira benefit from the drought?

> What is my biggest current risk?

## Architecture rule

The LLM receives established facts.

It does not create game facts.

Input should be a compact projection containing only relevant information:

- current turn
- current situation
- player exposure
- relevant markets
- relevant rivals
- top causal traces
- legal current actions

Do not send the entire database.

## Output

Use strict structured output validated by Pydantic.

Suggested conceptual response:

```json
{
  "answer": "Your farm income fell because the drought reduced output, but your stored grain increased in value as prices rose.",
  "observation_codes": [
    "farm_output_down",
    "grain_price_up",
    "inventory_value_up"
  ],
  "suggested_choice_ids": [
    "sell_stored_grain",
    "preserve_cash"
  ]
}
```

The suggested actions must reference actions already legal according to the engine.

## Testing

Normal tests use a fixture / fake LLM.

Live-model tests are separate smoke tests.

## Acceptance criteria

1. Advisor answers are grounded in engine-provided facts.
2. Invalid model output cannot reach gameplay code.
3. Model failure has a deterministic fallback message.
4. The advisor cannot mutate state.
5. Fixture-driven tests require no paid live model.
6. “Why did this happen?” answers align with causal trace data.

## Stop condition

Stop when the advisor improves understanding without becoming necessary to play.

---

# SECTION 18 — Bounded Free-Text Action Interpretation

**Status:** NOT STARTED

## Goal

Allow natural-language intent as a convenience layer over existing game commands.

Example:

> Spend about half my available cash buying cheap grain.

The LLM translates this into a typed draft.

Example:

```json
{
  "type": "buy_grain",
  "budget_policy": "fraction_of_cash",
  "budget_value_bps": 5000
}
```

## Confirmation rule

Free-text actions never execute immediately.

Show a player-readable draft:

```text
I understood this as:

Buy grain
Maximum spend: 50% of available cash

[Do it]
[Change]
```

The player confirms.

The confirmed command still passes normal game-rule validation.

## Unsupported intent

If the player requests something unavailable in the current world, return an unsupported result rather than inventing functionality.

## Acceptance criteria

1. Free text produces only known typed commands or an unsupported result.
2. Drafts are tied to a state revision.
3. A stale draft cannot execute after the game advances.
4. Confirmation is always required.
5. The LLM cannot directly mutate state.
6. Normal predefined buttons remain fully usable without an LLM.

## Stop condition

Stop when natural language is a useful shortcut rather than a second game engine.

---

# SECTION 19 — Authentication and Account Model

**Status:** NOT STARTED

## Goal

Add user accounts only when cross-device save, persistent player history, or external testing genuinely requires them.

## In scope

Choose and integrate the account provider deliberately.

Map external identity to an internal user id.

Do not duplicate unnecessary profile data.

Add authenticated API ownership checks.

Add automated test authentication using the provider's supported testing approach.

## Child / public release gate

Before public release, explicitly decide whether the product is:

- 13+

or

- designed with a reviewed child / parent privacy model suitable for younger users

Do not casually launch an authenticated conversational product for children without making this decision.

## Acceptance criteria

1. Users can only load and mutate their own runs.
2. Tests do not rely on an unsafe production auth bypass.
3. Authentication is not coupled into the simulation engine.
4. Public-launch age/privacy decision is documented before public release.

## Stop condition

Stop when accounts solve an actual product need rather than merely matching the original architecture diagram.

---

# SECTION 20 — Visual Asset System and Polish

**Status:** NOT STARTED

## Goal

Replace placeholders with a curated visual identity after the game loop has survived playtesting.

## In scope

Use pre-generated, human-reviewed artwork.

No runtime image generation is required for the game.

Create visual state variants only for states the current playable actually uses.

Examples:

```text
wheat_estate:
- healthy
- booming
- drought
- damaged

warehouse:
- empty
- normal
- full
- overflowing

river_market:
- quiet
- busy
- shortage
```

Support responsive image variants and stable asset ids.

Use subtle browser-native animation:

- count-up numbers
- card reveal motion
- drifting dust
- rain overlays
- subtle parallax
- market arrows
- disaster emphasis

Do not introduce a game rendering engine unless browser UI has demonstrated a concrete limitation.

## Acceptance criteria

1. Visual state is selected from simulation state, not inferred from image metadata.
2. Assets have stable ids and alt text.
3. The main mobile screen remains performant.
4. Artwork improves legibility and emotional payoff rather than adding clutter.
5. Outcome reveals receive the highest polish priority.

## Stop condition

Stop when the game feels like a tycoon game rather than a business dashboard.

---

# SECTION 21 — Production Deployment and Observability

**Status:** NOT STARTED

## Goal

Deploy the tested game as a simple production monolith.

## Preferred architecture

Keep deployment deliberately boring:

```text
React / TypeScript frontend
        ↓
FastAPI JSON API
        ↓
PostgreSQL
```

Static assets may use object storage plus a CDN when asset volume warrants it.

Do not add:

- Redis
- Kafka
- Celery
- microservices
- background workers

unless a measured production need appears.

## Observability

Use structured logging with:

- request id
- user id when known
- game run id when known
- state revision
- turn-resolution duration
- model-call metadata when applicable

Never log secrets.

Raw LLM prompt logging should be disabled by default in production.

## Acceptance criteria

1. Production can create, save, load, and complete a run.
2. Database migrations are controlled.
3. Turn resolution remains synchronous and fast enough for interactive use.
4. Logs support investigation of a reported bad turn.
5. Deployment does not introduce distributed infrastructure without need.

## Stop condition

Stop when the current MVP is stable enough for external testers.

---

# SECTION 22 — Architecture Expansion Test for Future Eras

**Status:** NOT STARTED

## Goal

Only after a successful Agricultural + City & Craft prototype, test whether the engine kernel is sufficiently general for very different future economics.

Do not implement full future ages.

## In scope

Create tiny non-playable architecture fixtures representing different mechanics.

### Industrial fixture

Demonstrate:

- high fixed cost
- capacity utilization
- mechanization
- lower marginal labor requirement
- transport / energy exposure

### Information or software fixture

Demonstrate:

- high upfront development cost
- low marginal reproduction cost
- demand or network sensitivity
- fast information movement

These fixtures exist to reveal whether the core model accidentally assumes agricultural production everywhere.

## Architecture principle

Use a common kernel plus explicit mechanic modules.

Do not force every age into one flat list of weights if that obscures meaningful differences.

## Acceptance criteria

1. Both fixtures can use the common engine shell without pretending to be farms.
2. New mechanics are explicit and typed.
3. No giant universal formula or arbitrary expression language is introduced.
4. The Agricultural game continues to pass unchanged.
5. Shared abstractions exist only where concrete reuse is demonstrated.

## Stop condition

Stop when the engine is proven extensible across at least two genuinely different economic production models.

---

# Part V — Deferred Long-Term Systems

## 23. Systems Explicitly Deferred Until Proven Necessary

The following are part of the long-term vision but are **not authorized** unless a future numbered section is created for them:

- complete eight-age authored content
- full City & Craft campaign
- Merchant Age
- Industrial Age
- Mass Market Age
- Information Age
- Automation Age
- multiplayer
- Steam integration
- native iOS / Android applications
- detailed geographic map
- individual worker simulation
- hundreds of commodities
- complex order books
- runtime AI image generation
- voice conversations
- LLM-driven canonical economy simulation
- unrestricted open-ended tools
- complete durable event sourcing as a product requirement
- microservices
- Redis
- background task infrastructure
- negotiation chat
- LLM narrative renderer

A future section may authorize one of these when player evidence and implementation needs justify it.

---

# Part VI — Eventual Product Direction

## 24. Future Agricultural MVP Shape

If the ordered prototype succeeds, the Agricultural chapter may eventually grow toward:

- approximately 10–15 meaningful turns
- a deep grain economy
- a smaller number of differentiated secondary goods
- 3 major rivals
- authored settlement / trade / scarcity / consolidation beats
- several coherent stochastic pressure systems
- visually rich business and world states
- advisor support
- optional bounded natural-language actions
- concrete legacy outcomes
- transition into City & Craft

The target is strategic richness, not a content-count checklist.

---

## 25. Future Dynasty and Legacy Direction

The player should eventually control a house, lineage, or dynasty rather than an implausibly immortal individual.

Each era may feature a descendant inheriting some combination of:

- capital
- reputation
- knowledge
- connections
- influence
- concrete legacy advantages

Player-facing legacy should favor tangible effects over abstract scorekeeping.

Examples:

- Granary Expertise
- River Contracts
- Land Network
- Workshop Patronage
- Crisis Reputation

These should change future decisions rather than merely increase a score.

---

## 26. Future Market and Information Direction

No-map gameplay can still include geography through named economic nodes and routes.

Future expansions may add:

- additional settlements
- sea routes
- road routes
- regional political boundaries
- route reliability
- information delay
- local versus distant price certainty
- trade relationships
- insurance
- finance

These should be presented as strategic economic networks, not spatial building placement.

---

## 27. Future Rival Direction

Rivals should persist long enough to create memory and identity.

Future systems may include:

- rival houses or dynasties
- descendants
- alliances
- long-term grudges
- trade partnerships
- acquisitions
- distress
- specialization
- strategic imitation

Canonical rival behavior remains simulation-driven.

LLMs may add conversational texture but must not invent economic state.

---

## 28. Future LLM Direction

The intended order of LLM capability is:

1. Grounded advisor
2. Bounded action interpreter
3. Negotiation
4. Narrative renderer

Never reverse the source-of-truth boundary.

Correct:

```text
engine creates fact
→ LLM explains fact
```

Incorrect:

```text
LLM invents reward
→ engine accepts reward as reality
```

Every structured LLM output must be validated before application use.

---

# Part VII — Definition of MVP Success

## 29. Player Experience Success Criteria

The MVP succeeds if a new player can:

1. Start on a phone without instruction.
2. Understand what they own and what the immediate opportunity is.
3. Make strategic choices without manipulating dense spreadsheets.
4. Form a prediction about what a choice might do.
5. See consequences that are surprising but understandable.
6. Experience a bad event whose impact depends on prior preparation.
7. Recognize at least one rival's strategic identity.
8. Feel their economic operation become visibly larger.
9. Experience at least one change in the economic bottleneck.
10. Want to make one more decision.

The most important question is:

> **Does the player want to make one more decision?**

---

## 30. Technical Success Criteria

Before calling the MVP technically sound:

```text
same seed + same actions + same ruleset = same world

canonical economic state uses deterministic integer representations

world disruptions change economic inputs rather than directly scripting every downstream result

causal traces explain major state changes

rivals make deterministic legal economic decisions

frontend never reconstructs canonical economic truth

mutations use revision checks once a server boundary exists

saved runs record ruleset/content/schema versions once persistence exists

LLMs never directly mutate game state

normal automated tests never require paid model calls

future-era abstractions are introduced only after concrete reuse is demonstrated
```

---

# Part VIII — Agent Guardrails

## 31. Do Not Build Ahead

The coding agent must not add infrastructure because it “will probably be useful later.”

Examples of forbidden anticipatory work:

- adding Redis before a queue exists
- adding auth before user accounts are needed
- adding SQLAlchemy before persistence is active
- creating empty schemas for eight ages
- building a generic event DSL for one drought
- building a plugin system for three operations
- building a universal formula engine
- adding an LLM gateway before an LLM feature is authorized
- creating microservices around a small synchronous simulation

If the current section can be completed cleanly without an abstraction, prefer the simpler implementation.

---

## 32. Do Not Rewrite Working Systems Without Evidence

Before replacing an existing working subsystem, the plan must state:

1. What concrete problem exists.
2. Why a targeted change cannot solve it.
3. What acceptance criterion the rewrite improves.
4. What regression tests protect existing behavior.

Refactoring is allowed when it reduces complexity or enables the active section, but not merely to impose a preferred architecture style.

---

## 33. Dependencies Require Justification

Before adding a dependency, the implementation plan should state:

- what problem it solves
- why the standard library or existing dependency is insufficient
- whether the dependency enters the pure engine boundary
- whether it creates runtime or operational complexity

Prefer fewer dependencies in the simulation core.

---

## 34. Agent Completion Report Template

At the end of each section, report:

```text
SECTION COMPLETED:

Files changed:
- ...

Behavior added:
- ...

Commands run:
- ...

Acceptance checks:
- [pass/fail] ...

Known risks:
- ...

Deferred observations:
- ...

Did not implement:
- list any tempting future work intentionally left out
```

Then stop.

---

# Part IX — Suggested Immediate Start

## 35. First Active Section

Begin with:

> **SECTION 1 — Repository Contract and Walking Skeleton**

After Section 1 passes, move to Section 2.

Do not ask the agent to implement the complete MVP from this file in a single run.

A good session-opening instruction is:

```text
Read BUILD_SPEC.md completely for context.

Work only on SECTION 1.

Treat future sections as context, not scope.

Inspect the repository first.
Use /plan.
Then /grill the plan for unnecessary abstraction and future work.
Only after the plan is approved, use /goal to implement it.

Run every acceptance check from SECTION 1.
Stop when SECTION 1 is complete.
Do not begin SECTION 2.
```

For later sections, replace `SECTION 1` with the active section number.

---

# Final Architectural Principle

If every developer and coding agent remembers one rule, it should be this:

> **Historical Empire is a deterministic, typed economic simulation wrapped in a story system. The player makes strategic decisions; authored history creates pressures; the simulation creates consequences; the UI makes those consequences satisfying and understandable; LLMs may interpret and explain but never define economic reality.**

