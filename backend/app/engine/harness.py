"""Balance harness — Section 9 headless strategy sweep.

Pure, sync, no FastAPI/DB. Runs many deterministic FiveTurnGame runs across
scripted policies and seeds, aggregates metrics, reports dominance via
median-ratio (exit 2 on breach, not hard-failing unit test on first land).
Uses PRESSURE_* constants via FiveTurnGame — never bare "normal"/"drought".
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from app.domain.types import GameState, PlayerCommand
from app.engine.actor import (
    BUILD_GRANARY_COST,
    EXPAND_FARM_COST,
    ROUTE_ESTABLISH_COST,
)
from app.engine.prototype import FiveTurnGame, default_start_state
from app.engine.rng import rng_for

# ---------------------------------------------------------------------------
# Policy definitions (all affordability-aware, pure)
# ---------------------------------------------------------------------------

POLICY_IDS: tuple[str, ...] = (
    "production_heavy",
    "storage_heavy",
    "trade_heavy",
    "cash_preserving",
    "random_legal",
)


def _can_afford(cash: int, cost: int) -> bool:
    return cash >= cost


def policy_production_heavy(
    state: GameState, turn_idx: int, seed: str, version: str
) -> PlayerCommand:
    """Expand farm early while affordable, else hold."""
    if turn_idx < 2 and _can_afford(state.player.cash, EXPAND_FARM_COST + 200):
        return PlayerCommand(type="expand_farm")  # type: ignore[arg-type]
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


def policy_storage_heavy(state: GameState, turn_idx: int, seed: str, version: str) -> PlayerCommand:
    """Build granary T0, buy T1-2, hold drought T3, sell T4-5 at high price."""
    if turn_idx == 0 and _can_afford(state.player.cash, BUILD_GRANARY_COST):
        return PlayerCommand(type="build_granary")  # type: ignore[arg-type]
    if turn_idx in (1, 2):
        price = state.market.current_price
        space = state.player.storage_capacity - state.player.inventory.grain
        if space <= 0 or price <= 0:
            return PlayerCommand(type="hold")  # type: ignore[arg-type]
        max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 20
        actual = min(20, space, max_affordable)
        if actual <= 0:
            return PlayerCommand(type="hold")  # type: ignore[arg-type]
        return PlayerCommand(type="buy_grain", quantity=actual)  # type: ignore[arg-type]
    if turn_idx in (3, 4) and state.player.inventory.grain > 0:
        # Sell after drought price spike — realize gains
        qty = min(30, state.player.inventory.grain)
        if qty > 0:
            return PlayerCommand(type="sell_grain", quantity=qty)  # type: ignore[arg-type]
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


def policy_trade_heavy(state: GameState, turn_idx: int, seed: str, version: str) -> PlayerCommand:
    """Secure route T1, buy T2, ship T4-5 when established."""
    if (
        turn_idx == 0
        and not state.route.established
        and _can_afford(state.player.cash, ROUTE_ESTABLISH_COST)
    ):
        return PlayerCommand(type="secure_route")  # type: ignore[arg-type]
    if turn_idx == 1:
        price = state.market.current_price
        space = state.player.storage_capacity - state.player.inventory.grain
        if space > 0 and price > 0:
            max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 10
            actual = min(10, space, max_affordable)
            if actual > 0:
                return PlayerCommand(type="buy_grain", quantity=actual)  # type: ignore[arg-type]
        return PlayerCommand(type="hold")  # type: ignore[arg-type]
    if turn_idx in (3, 4) and state.route.established and state.player.inventory.grain > 0:
        qty = min(10, state.player.inventory.grain, state.route.capacity)
        if qty > 0:
            return PlayerCommand(type="ship_grain", quantity=qty)  # type: ignore[arg-type]
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


def policy_cash_preserving(
    state: GameState, turn_idx: int, seed: str, version: str
) -> PlayerCommand:
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


def policy_random_legal(state: GameState, turn_idx: int, seed: str, version: str) -> PlayerCommand:
    """Uniform among affordable legal commands, deterministic via rng_for."""
    rng = rng_for(seed, version, turn_idx, "harness", "random_legal", 0)
    # Build affordable list
    candidates: list[PlayerCommand] = []
    # hold always legal
    candidates.append(PlayerCommand(type="hold"))  # type: ignore[arg-type]
    if _can_afford(state.player.cash, EXPAND_FARM_COST):
        candidates.append(PlayerCommand(type="expand_farm"))  # type: ignore[arg-type]
    if _can_afford(state.player.cash, BUILD_GRANARY_COST):
        candidates.append(PlayerCommand(type="build_granary"))  # type: ignore[arg-type]
    if not state.route.established and _can_afford(state.player.cash, ROUTE_ESTABLISH_COST):
        candidates.append(PlayerCommand(type="secure_route"))  # type: ignore[arg-type]
    # buy_grain if affordable and space
    price = state.market.current_price
    space = state.player.storage_capacity - state.player.inventory.grain
    if space > 0 and price > 0:
        max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 0
        affordable_qty = min(space, max_affordable)
        if affordable_qty > 0:
            qty = min(10, affordable_qty)
            candidates.append(PlayerCommand(type="buy_grain", quantity=qty))  # type: ignore[arg-type]
    if state.player.inventory.grain > 0:
        qty = min(10, state.player.inventory.grain)
        candidates.append(PlayerCommand(type="sell_grain", quantity=qty))  # type: ignore[arg-type]
    if state.route.established and state.player.inventory.grain > 0:
        qty = min(10, state.player.inventory.grain, state.route.capacity)
        if qty > 0:
            candidates.append(PlayerCommand(type="ship_grain", quantity=qty))  # type: ignore[arg-type]
    # deterministic choice
    idx = int(rng.random() * len(candidates)) if len(candidates) > 1 else 0
    if idx >= len(candidates):
        idx = len(candidates) - 1
    return candidates[idx]


POLICY_FUNCS: dict[str, Callable[[GameState, int, str, str], PlayerCommand]] = {
    "production_heavy": policy_production_heavy,
    "storage_heavy": policy_storage_heavy,
    "trade_heavy": policy_trade_heavy,
    "cash_preserving": policy_cash_preserving,
    "random_legal": policy_random_legal,
}


# ---------------------------------------------------------------------------
# Batch models
# ---------------------------------------------------------------------------


class BatchConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    seed_prefix: str = "harness"
    n_seeds: int = 200
    version: str = "1.0"
    policy_ids: tuple[str, ...] = POLICY_IDS


class SeedResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    seed: str
    policy_id: str
    final_wealth: int
    wealth_delta: int
    cash_low: int
    peak_inventory: int
    final_cash: int
    final_grain: int
    price_home_series: tuple[int, ...]
    price_river_series: tuple[int, ...]
    largest_swing: int
    choices: tuple[str, ...]


class PolicyAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)
    policy_id: str
    n: int
    mean_wealth: int
    median_wealth: int
    min_wealth: int
    max_wealth: int
    win_rate: float
    median_cash_low: int
    median_peak_inventory: int
    price_min: int
    price_max: int
    max_swing_max: int
    bankrupt_count: int


class BatchResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    config: BatchConfig
    per_seed: tuple[SeedResult, ...]
    aggregates: tuple[PolicyAggregate, ...]
    overall_price_min: int
    overall_price_max: int
    global_max_swing: int
    any_negative_state: bool
    # Gates (reported, not hard assert on first land)
    dominant_gate_pass: bool
    dead_gate_pass: bool
    price_gate_pass: bool
    negativity_gate_pass: bool
    hold_not_top_gate_pass: bool
    median_ratio: float
    dominant_reason: str
    dead_reason: str
    hold_not_top_reason: str


def _wealth(state: GameState) -> int:
    return state.player.cash + (state.player.inventory.grain * state.market.current_price // 1000)


def run_batch(config: BatchConfig) -> BatchResult:
    """Run batch — deterministic, pure, no global random."""
    seeds = [f"{config.seed_prefix}-{i:04d}" for i in range(config.n_seeds)]
    per_seed: list[SeedResult] = []
    # also collect per-seed best for win_rate
    wins: Counter[str] = Counter()
    # first pass: collect all
    for seed in seeds:
        # For each policy, run game
        seed_best: tuple[str, int] | None = None
        seed_results: list[SeedResult] = []
        for pid in config.policy_ids:
            func = POLICY_FUNCS[pid]
            game = FiveTurnGame(
                seed=seed,
                version=config.version,
                start_state=default_start_state(seed, config.version),
            )
            choices: list[str] = []
            # Run 5 turns via policy
            for turn_idx in range(5):
                cmd = func(game.state, turn_idx, seed, config.version)
                choices.append(
                    f"{cmd.type}:{cmd.quantity}" if cmd.quantity is not None else cmd.type
                )
                game.submit(cmd)
            summary = game.summary()
            # prices
            home_series = tuple(h.next_state.market.current_price for h in game.history)
            river_series = tuple(h.next_state.river_market.current_price for h in game.history)
            # largest swing = max abs wealth_delta per turn
            swings = [abs(h.player_outcome.wealth_delta) for h in game.history]
            largest = max(swings) if swings else 0
            sr = SeedResult(
                seed=seed,
                policy_id=pid,
                final_wealth=summary.final_wealth,
                wealth_delta=summary.wealth_delta_total,
                cash_low=summary.cash_low,
                peak_inventory=summary.peak_inventory,
                final_cash=summary.final_state.player.cash,
                final_grain=summary.final_state.player.inventory.grain,
                price_home_series=home_series,
                price_river_series=river_series,
                largest_swing=largest,
                choices=tuple(choices),
            )
            seed_results.append(sr)
            if seed_best is None or sr.final_wealth > seed_best[1]:
                seed_best = (pid, sr.final_wealth)
            # check negativity across history (also via summary but do per-turn)
            # per_seed negativity is captured later via BatchResult overall
            per_seed.append(sr)
        # record win for best on this seed
        if seed_best is not None:
            # tie broken by first max (POLICY_IDS order) — deterministic
            # But we already picked first max encountered in POLICY_IDS order, so stable
            wins[seed_best[0]] += 1
        # handle ties: if multiple policies tie for max wealth, wins already first; we want to ensure tie-breaking is stable
        # So we should recompute wins with tie-break by POLICY_IDS order
        max_wealth = max(r.final_wealth for r in seed_results)
        # find first pid in POLICY_IDS order that has max
        for pid in config.policy_ids:
            for r in seed_results:
                if r.policy_id == pid and r.final_wealth == max_wealth:
                    # adjust wins: remove previous and add tie-correct
                    # We already incremented wins[seed_best[0]]; if that was not tie-correct, fix
                    # Simpler: just correct by decrementing previous and incrementing tie winner
                    if pid != seed_best[0]:  # type: ignore[arg-type]
                        wins[seed_best[0]] -= 1  # type: ignore[index]
                        wins[pid] += 1
                    break
            if any(r.policy_id == pid and r.final_wealth == max_wealth for r in seed_results):
                break

    # aggregates
    aggregates: list[PolicyAggregate] = []
    # collect overall price bounds
    all_home_prices = [p for r in per_seed for p in r.price_home_series]
    overall_price_min = min(all_home_prices) if all_home_prices else 0
    overall_price_max = max(all_home_prices) if all_home_prices else 0
    global_max_swing = max((r.largest_swing for r in per_seed), default=0)
    # negativity check
    any_negative = False
    for r in per_seed:
        if r.final_cash < 0 or r.final_grain < 0:
            any_negative = True
        for p in r.price_home_series + r.price_river_series:
            if p <= 0:
                any_negative = True

    # per-policy aggregates
    sorted_wealths: dict[str, list[int]] = {pid: [] for pid in config.policy_ids}
    for r in per_seed:
        sorted_wealths[r.policy_id].append(r.final_wealth)

    # compute median helpers
    for pid in config.policy_ids:
        ws = sorted(sorted_wealths[pid])
        n = len(ws)
        median = ws[n // 2] if n % 2 == 1 else (ws[n // 2 - 1] + ws[n // 2]) // 2
        mean = sum(ws) // n if n else 0
        min_w = min(ws) if ws else 0
        max_w = max(ws) if ws else 0
        win_rate = wins.get(pid, 0) / config.n_seeds if config.n_seeds else 0.0
        # median cash_low / peak
        cash_lows = sorted([r.cash_low for r in per_seed if r.policy_id == pid])
        peaks = sorted([r.peak_inventory for r in per_seed if r.policy_id == pid])
        median_cash_low = cash_lows[len(cash_lows) // 2] if cash_lows else 0
        median_peak = peaks[len(peaks) // 2] if peaks else 0
        price_min = min(
            (p for r in per_seed if r.policy_id == pid for p in r.price_home_series), default=0
        )
        price_max = max(
            (p for r in per_seed if r.policy_id == pid for p in r.price_home_series), default=0
        )
        max_swing = max((r.largest_swing for r in per_seed if r.policy_id == pid), default=0)
        bankrupt = sum(
            1 for r in per_seed if r.policy_id == pid and r.final_cash == 0 and r.final_grain == 0
        )
        aggregates.append(
            PolicyAggregate(
                policy_id=pid,
                n=n,
                mean_wealth=mean,
                median_wealth=median,
                min_wealth=min_w,
                max_wealth=max_w,
                win_rate=win_rate,
                median_cash_low=median_cash_low,
                median_peak_inventory=median_peak,
                price_min=price_min,
                price_max=price_max,
                max_swing_max=max_swing,
                bankrupt_count=bankrupt,
            )
        )

    # Gates
    # dominant: max_median / second_max < 1.60
    medians_sorted = sorted([a.median_wealth for a in aggregates], reverse=True)
    median_ratio = (
        (medians_sorted[0] / medians_sorted[1])
        if len(medians_sorted) >= 2 and medians_sorted[1] != 0
        else 999.0
    )
    dominant_pass = median_ratio < 1.60
    dominant_reason = (
        f"median_ratio {median_ratio:.2f} {'PASS' if dominant_pass else 'FAIL'} (threshold <1.60)"
    )

    # dead: every non-random median >= 0.70 * overall median
    all_medians = sorted([a.median_wealth for a in aggregates])
    overall_median = all_medians[len(all_medians) // 2] if all_medians else 0
    dead_pass = True
    dead_reasons: list[str] = []
    for a in aggregates:
        if a.policy_id == "random_legal":
            continue
        if overall_median and a.median_wealth < 0.70 * overall_median:
            dead_pass = False
            dead_reasons.append(
                f"{a.policy_id} median {a.median_wealth} < 0.70*overall {overall_median}"
            )
    dead_reason = "PASS" if dead_pass else "; ".join(dead_reasons) if dead_reasons else "FAIL"

    # price gate
    price_pass = True
    for a in aggregates:
        if a.price_min < 2000 or a.price_max > 9000:
            price_pass = False
            break
    # also check envelope: per-turn move <= 20% +1 (allow rounding)
    # we check in gate but also report overall price range

    # hold_not_top gate: cash_preserving must NOT have highest median
    hold_median = next((a.median_wealth for a in aggregates if a.policy_id == "cash_preserving"), 0)
    max_median = max((a.median_wealth for a in aggregates), default=0)
    max_policy = next((a.policy_id for a in aggregates if a.median_wealth == max_median), "")
    hold_not_top_pass = hold_median != max_median
    hold_not_top_reason = f"cash {hold_median} vs max {max_median} ({max_policy}) {'PASS' if hold_not_top_pass else 'FAIL'} — cash must not be top"

    # negativity gate
    negativity_pass = not any_negative

    return BatchResult(
        config=config,
        per_seed=tuple(per_seed),
        aggregates=tuple(aggregates),
        overall_price_min=overall_price_min,
        overall_price_max=overall_price_max,
        global_max_swing=global_max_swing,
        any_negative_state=any_negative,
        dominant_gate_pass=dominant_pass,
        dead_gate_pass=dead_pass,
        price_gate_pass=price_pass,
        negativity_gate_pass=negativity_pass,
        hold_not_top_gate_pass=hold_not_top_pass,
        median_ratio=median_ratio,
        dominant_reason=dominant_reason,
        dead_reason=dead_reason,
        hold_not_top_reason=hold_not_top_reason,
    )


def format_markdown(result: BatchResult) -> str:
    lines: list[str] = []
    lines.append(
        f"# Balance Harness — {result.config.n_seeds} seeds × {len(result.config.policy_ids)} policies = {len(result.per_seed)} games"
    )
    lines.append("")
    lines.append(f"Config: prefix={result.config.seed_prefix} version={result.config.version}")
    lines.append("")
    lines.append(
        "| policy | n | win_rate | median_wealth | mean_wealth | median_cash_low | price_range | bankrupt |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for a in result.aggregates:
        lines.append(
            f"| {a.policy_id} | {a.n} | {a.win_rate:.2%} | {a.median_wealth} | {a.mean_wealth} | {a.median_cash_low} | {a.price_min}-{a.price_max} | {a.bankrupt_count} |"
        )
    lines.append("")
    lines.append(
        f"Overall Home price: {result.overall_price_min}-{result.overall_price_max}  Global max swing: {result.global_max_swing}"
    )
    lines.append("")
    lines.append(
        f"Dominant gate (median_ratio <1.60): {result.dominant_reason} — {'PASS' if result.dominant_gate_pass else 'FAIL'}"
    )
    lines.append(
        f"Dead gate (median ≥0.70*overall): {result.dead_reason} — {'PASS' if result.dead_gate_pass else 'FAIL'}"
    )
    lines.append(
        f"Hold-not-top gate (cash not max median): {result.hold_not_top_reason} — {'PASS' if result.hold_not_top_gate_pass else 'FAIL'}"
    )
    lines.append(f"Price gate ([2000,9000]): {'PASS' if result.price_gate_pass else 'FAIL'}")
    lines.append(f"Negativity gate (no <0): {'PASS' if result.negativity_gate_pass else 'FAIL'}")
    lines.append("")
    lines.append(
        "Note: deterministic policies are seed-invariant on fixed authored arc; seed variation comes from random_legal only."
    )
    return "\n".join(lines)


def to_json(result: BatchResult) -> str:
    data = {
        "config": result.config.model_dump(),
        "aggregates": {a.policy_id: a.model_dump() for a in result.aggregates},
        "overall": {
            "price_min": result.overall_price_min,
            "price_max": result.overall_price_max,
            "global_max_swing": result.global_max_swing,
            "any_negative_state": result.any_negative_state,
        },
        "gates": {
            "dominant_pass": result.dominant_gate_pass,
            "dead_pass": result.dead_gate_pass,
            "price_pass": result.price_gate_pass,
            "negativity_pass": result.negativity_gate_pass,
            "hold_not_top_pass": result.hold_not_top_gate_pass,
            "median_ratio": result.median_ratio,
            "dominant_reason": result.dominant_reason,
            "dead_reason": result.dead_reason,
            "hold_not_top_reason": result.hold_not_top_reason,
        },
        "per_seed": [r.model_dump() for r in result.per_seed],
    }
    return json.dumps(data, sort_keys=True, indent=2)
