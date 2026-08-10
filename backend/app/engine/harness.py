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

INTENTIONAL_POLICY_IDS: tuple[str, ...] = (
    "production_heavy",
    "storage_heavy",
    "trade_heavy",
    "cash_preserving",
)


def _can_afford(cash: int, cost: int) -> bool:
    return cash >= cost


def policy_production_heavy(
    state: GameState, turn_idx: int, seed: str, version: str
) -> PlayerCommand:
    """Production: expand farm aggressively early, sell surplus that won't fit.

    Strategy: invest cash into capacity when affordable; after expanding, sell
    each turn the amount that would overflow storage after the next harvest
    rather than hoarding into a cap and dumping at the end. This avoids
    harvest waste (capped_by_storage) while still carrying profitable grain.
    """
    from app.engine.actor import YIELD_PER_CAPACITY

    if turn_idx < 2 and _can_afford(state.player.cash, EXPAND_FARM_COST + 50):
        return PlayerCommand(type="expand_farm")  # type: ignore[arg-type]
    if turn_idx == 2 and _can_afford(state.player.cash, EXPAND_FARM_COST + 50):
        return PlayerCommand(type="expand_farm")  # type: ignore[arg-type]
    # After expansion, sell surplus that will not fit after next harvest.
    # Use normal yield as predictor (drought only reduces output, so this is
    # conservative — we never sell more than would overflow on a normal turn).
    predicted_output = state.player.farm_capacity * YIELD_PER_CAPACITY
    predicted_after_harvest = state.player.inventory.grain + predicted_output
    if predicted_after_harvest > state.player.storage_capacity and state.player.inventory.grain > 0:
        surplus = predicted_after_harvest - state.player.storage_capacity
        qty = min(surplus, state.player.inventory.grain)
        if qty > 0:
            return PlayerCommand(type="sell_grain", quantity=qty)  # type: ignore[arg-type]
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


def policy_storage_heavy(state: GameState, turn_idx: int, seed: str, version: str) -> PlayerCommand:
    """Storage: build on overflow, buy only into headroom harvest will not claim.

    Strategy: granary stores free harvest that would otherwise be wasted
    (capped_by_storage) rather than purchased grain (~2.6/unit vs ~8.5/unit).
    Build only when incoming harvest would overflow current storage; buy only
    into space that harvest will not fill (headroom = storage - (inventory+harvest)).
    Sell large at price peak (turn 4). No constant tuning needed.
    """
    from app.engine.actor import YIELD_PER_CAPACITY

    harvest = state.player.farm_capacity * YIELD_PER_CAPACITY
    # Build when harvest would overflow and still turns remain to benefit (turn<4)
    if turn_idx < 4 and state.player.inventory.grain + harvest > state.player.storage_capacity:
        if _can_afford(state.player.cash, BUILD_GRANARY_COST):
            return PlayerCommand(type="build_granary")  # type: ignore[arg-type]
    # Buy only into headroom harvest will not claim
    headroom = state.player.storage_capacity - (state.player.inventory.grain + harvest)
    if headroom > 0 and turn_idx in (1, 2):
        price = state.market.current_price
        max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 0
        target = min(headroom, max_affordable)
        actual = min(target, 80) if target > 10 else target
        if actual > 0:
            return PlayerCommand(type="buy_grain", quantity=actual)  # type: ignore[arg-type]
    if turn_idx == 4 and state.player.inventory.grain > 0:
        qty = min(state.player.inventory.grain, 150)
        if qty > 0:
            return PlayerCommand(type="sell_grain", quantity=qty)  # type: ignore[arg-type]
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


def policy_trade_heavy(state: GameState, turn_idx: int, seed: str, version: str) -> PlayerCommand:
    """Trade: secure route early, ship every profitable turn, stop when not.

    Strategy: pay route cost early, then each turn evaluate ship margin
    (river_price - transport_cost - home_price). If margin >0 and inventory
    exists, ship up to capacity/inventory/cash. Otherwise, deploy cash into
    grain while space exists (buy scaled pre-drought). At turn 4 when margin
    is negative (home famine premium), sell remaining inventory at Home peak
    rather than shipping at a loss.
    """
    if (
        turn_idx == 0
        and not state.route.established
        and _can_afford(state.player.cash, ROUTE_ESTABLISH_COST)
    ):
        return PlayerCommand(type="secure_route")  # type: ignore[arg-type]
    # For any turn where route is established, consider shipping if profitable.
    if state.route.established and state.player.inventory.grain > 0:
        margin = (
            state.river_market.current_price
            - state.route.transport_cost_per_unit
            - state.market.current_price
        )
        if margin > 0:
            # Affordable by transport cost
            cost_per = state.route.transport_cost_per_unit
            if cost_per <= 0:
                affordable_ship = state.player.inventory.grain
            else:
                affordable_ship = ((state.player.cash + 1) * 1000 - 1) // cost_per
            ship_qty = min(
                state.player.inventory.grain,
                state.route.capacity,
                affordable_ship,
            )
            if ship_qty > 0:
                return PlayerCommand(type="ship_grain", quantity=ship_qty)  # type: ignore[arg-type]
    # Not shipping (margin <=0 or no inventory): buy scaled pre-drought or sell at peak
    if turn_idx in (1, 2):
        price = state.market.current_price
        space = state.player.storage_capacity - state.player.inventory.grain
        if space > 0 and price > 0:
            max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 0
            target = min(space, max_affordable)
            actual = min(target, 80) if target > 10 else target
            if actual > 0:
                return PlayerCommand(type="buy_grain", quantity=actual)  # type: ignore[arg-type]
        return PlayerCommand(type="hold")  # type: ignore[arg-type]
    if turn_idx == 4 and state.player.inventory.grain > 0:
        qty = min(state.player.inventory.grain, 80)
        if qty > 0:
            return PlayerCommand(type="sell_grain", quantity=qty)  # type: ignore[arg-type]
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


def _policy_trade_heavy_no_route(
    state: GameState, turn_idx: int, seed: str, version: str
) -> PlayerCommand:
    """Matched control: identical to trade_heavy but never secures route."""
    # Never secure route; otherwise same ship-when-profitable logic (which will be no-op)
    if state.route.established and state.player.inventory.grain > 0:
        margin = (
            state.river_market.current_price
            - state.route.transport_cost_per_unit
            - state.market.current_price
        )
        if margin > 0:
            cost_per = state.route.transport_cost_per_unit
            if cost_per <= 0:
                affordable_ship = state.player.inventory.grain
            else:
                affordable_ship = ((state.player.cash + 1) * 1000 - 1) // cost_per
            ship_qty = min(
                state.player.inventory.grain,
                state.route.capacity,
                affordable_ship,
            )
            if ship_qty > 0:
                return PlayerCommand(type="ship_grain", quantity=ship_qty)  # type: ignore[arg-type]
    if turn_idx in (1, 2):
        price = state.market.current_price
        space = state.player.storage_capacity - state.player.inventory.grain
        if space > 0 and price > 0:
            max_affordable = ((state.player.cash + 1) * 1000 - 1) // price if price > 0 else 0
            target = min(space, max_affordable)
            actual = min(target, 80) if target > 10 else target
            if actual > 0:
                return PlayerCommand(type="buy_grain", quantity=actual)  # type: ignore[arg-type]
        return PlayerCommand(type="hold")  # type: ignore[arg-type]
    if turn_idx == 4 and state.player.inventory.grain > 0:
        qty = min(state.player.inventory.grain, 80)
        if qty > 0:
            return PlayerCommand(type="sell_grain", quantity=qty)  # type: ignore[arg-type]
    return PlayerCommand(type="hold")  # type: ignore[arg-type]


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
    win_rate_bps: int
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
    # Gates
    dominant_gate_pass: bool
    dead_gate_pass: bool
    price_gate_pass: bool
    negativity_gate_pass: bool
    hold_not_top_gate_pass: bool
    median_ratio_bps: int
    dominant_reason: str
    dead_reason: str
    hold_not_top_reason: str
    # Route incremental (matched control)
    trade_wealth: int
    trade_without_route_wealth: int
    route_incremental_value: int
    route_incremental_value_bps_of_cost: int
    # Tie handling
    tied_best_count: int
    # Overall median for dead/dominant integer math
    overall_median: int


def _wealth(state: GameState) -> int:
    return state.player.cash + (state.player.inventory.grain * state.market.current_price // 1000)


def run_batch(config: BatchConfig) -> BatchResult:
    """Run batch — deterministic, pure, no global random."""
    seeds = [f"{config.seed_prefix}-{i:04d}" for i in range(config.n_seeds)]
    per_seed: list[SeedResult] = []
    wins: Counter[str] = Counter()
    tied_best_count = 0
    for seed in seeds:
        seed_results: list[SeedResult] = []
        for pid in config.policy_ids:
            func = POLICY_FUNCS[pid]
            game = FiveTurnGame(
                seed=seed,
                version=config.version,
                start_state=default_start_state(seed, config.version),
            )
            choices: list[str] = []
            for turn_idx in range(5):
                cmd = func(game.state, turn_idx, seed, config.version)
                choices.append(
                    f"{cmd.type}:{cmd.quantity}" if cmd.quantity is not None else cmd.type
                )
                game.submit(cmd)
            summary = game.summary()
            home_series = tuple(h.next_state.market.current_price for h in game.history)
            river_series = tuple(h.next_state.river_market.current_price for h in game.history)
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
            per_seed.append(sr)
        # Determine unique winner and ties for this seed
        max_wealth = max(r.final_wealth for r in seed_results)
        best_ids = [r.policy_id for r in seed_results if r.final_wealth == max_wealth]
        if len(best_ids) == 1:
            wins[best_ids[0]] += 1
        else:
            tied_best_count += 1

    # aggregates
    aggregates: list[PolicyAggregate] = []
    all_home_prices = [p for r in per_seed for p in r.price_home_series]
    overall_price_min = min(all_home_prices) if all_home_prices else 0
    overall_price_max = max(all_home_prices) if all_home_prices else 0
    global_max_swing = max((r.largest_swing for r in per_seed), default=0)
    any_negative = False
    for r in per_seed:
        if r.final_cash < 0 or r.final_grain < 0:
            any_negative = True
        for p in r.price_home_series + r.price_river_series:
            if p <= 0:
                any_negative = True

    sorted_wealths: dict[str, list[int]] = {pid: [] for pid in config.policy_ids}
    for r in per_seed:
        sorted_wealths[r.policy_id].append(r.final_wealth)

    for pid in config.policy_ids:
        ws = sorted(sorted_wealths[pid])
        n = len(ws)
        median = ws[n // 2] if n % 2 == 1 else (ws[n // 2 - 1] + ws[n // 2]) // 2
        mean = sum(ws) // n if n else 0
        min_w = min(ws) if ws else 0
        max_w = max(ws) if ws else 0
        # win_rate_bps integer: unique wins *10000 // n_seeds
        win_bps = (wins.get(pid, 0) * 10_000 // config.n_seeds) if config.n_seeds else 0
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
                win_rate_bps=win_bps,
                median_cash_low=median_cash_low,
                median_peak_inventory=median_peak,
                price_min=price_min,
                price_max=price_max,
                max_swing_max=max_swing,
                bankrupt_count=bankrupt,
            )
        )

    # Gates — integer bps math, no floats
    # Build median lookup
    median_by_id = {a.policy_id: a.median_wealth for a in aggregates}
    # Dominant: top median vs second top <1.60  => top*10000 < second*16000
    medians_sorted = sorted([a.median_wealth for a in aggregates], reverse=True)
    if len(medians_sorted) >= 2 and medians_sorted[1] != 0:
        median_ratio_bps = medians_sorted[0] * 10_000 // medians_sorted[1]
        dominant_pass = medians_sorted[0] * 10_000 < medians_sorted[1] * 16_000
    else:
        median_ratio_bps = 99_999
        dominant_pass = False
    # Format ratio deterministically from bps
    ratio_int = median_ratio_bps // 10_000
    ratio_frac = median_ratio_bps % 10_000
    # Keep two decimal display but from integer
    dominant_reason = f"median_ratio {ratio_int}.{ratio_frac:04d} ({median_ratio_bps} bps) {'PASS' if dominant_pass else 'FAIL'} (threshold <1.60 = 16000 bps)"

    # Dead: overall median of all medians (including random) — integer
    all_medians = sorted([a.median_wealth for a in aggregates])
    overall_median = all_medians[len(all_medians) // 2] if all_medians else 0
    dead_pass = True
    dead_reasons: list[str] = []
    for a in aggregates:
        if a.policy_id == "random_legal":
            continue
        # integer: a.median*10000 >= overall*7000
        if overall_median and a.median_wealth * 10_000 < overall_median * 7_000:
            dead_pass = False
            dead_reasons.append(
                f"{a.policy_id} median {a.median_wealth} < 0.70*overall {overall_median} (bps check {a.median_wealth * 10_000} < {overall_median * 7_000})"
            )
    dead_reason = "PASS" if dead_pass else "; ".join(dead_reasons) if dead_reasons else "FAIL"

    # Price gate
    price_pass = True
    for a in aggregates:
        if a.price_min < 2000 or a.price_max > 9000:
            price_pass = False
            break

    # Hold rank over INTENTIONAL policies only, material 5%
    # Require >=2 of 3 active (prod,stor,trade) beat hold by >=5% => active*10000 >= hold*10500
    hold_median = median_by_id.get("cash_preserving", 0)
    active_ids = ("production_heavy", "storage_heavy", "trade_heavy")
    active_beats = 0
    for pid in active_ids:
        active_med = median_by_id.get(pid, 0)
        if hold_median and active_med * 10_000 >= hold_median * 10_500:
            active_beats += 1
    # Rank among intentional 4
    intentional_medians = [(pid, median_by_id[pid]) for pid in INTENTIONAL_POLICY_IDS]
    intentional_medians_sorted = sorted(intentional_medians, key=lambda x: -x[1])
    rank = next(
        (i for i, (pid, _) in enumerate(intentional_medians_sorted, 1) if pid == "cash_preserving"),
        1,
    )
    max_intentional_median = intentional_medians_sorted[0][1] if intentional_medians_sorted else 0
    max_intentional_pid = intentional_medians_sorted[0][0] if intentional_medians_sorted else ""
    hold_not_top_pass = active_beats >= 2
    hold_not_top_reason = (
        f"cash {hold_median} rank {rank}/4 intentional vs max {max_intentional_median} ({max_intentional_pid}) "
        f"{'PASS' if hold_not_top_pass else 'FAIL'} — {active_beats}/3 active beat hold by ≥5% "
        f"(need ≥2, hold rank ≥3 among 4); tied_best {tied_best_count}"
    )

    negativity_pass = not any_negative

    # Route incremental via matched control: trade_heavy vs trade_heavy_no_route
    # Run trade_without_route across same seeds to get median
    trade_without_wealths: list[int] = []
    for seed in seeds:
        game = FiveTurnGame(
            seed=seed,
            version=config.version,
            start_state=default_start_state(seed, config.version),
        )
        for turn_idx in range(5):
            cmd = _policy_trade_heavy_no_route(game.state, turn_idx, seed, config.version)
            game.submit(cmd)
        trade_without_wealths.append(game.summary().final_wealth)
    trade_without_sorted = sorted(trade_without_wealths)
    n_t = len(trade_without_sorted)
    trade_without_median = (
        trade_without_sorted[n_t // 2]
        if n_t % 2 == 1
        else (trade_without_sorted[n_t // 2 - 1] + trade_without_sorted[n_t // 2]) // 2
    )
    trade_median = median_by_id.get("trade_heavy", 0)
    route_inc = trade_median - trade_without_median
    route_bps = (route_inc * 10_000 // ROUTE_ESTABLISH_COST) if ROUTE_ESTABLISH_COST else 0

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
        median_ratio_bps=median_ratio_bps,
        dominant_reason=dominant_reason,
        dead_reason=dead_reason,
        hold_not_top_reason=hold_not_top_reason,
        trade_wealth=trade_median,
        trade_without_route_wealth=trade_without_median,
        route_incremental_value=route_inc,
        route_incremental_value_bps_of_cost=route_bps,
        tied_best_count=tied_best_count,
        overall_median=overall_median,
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
        "| policy | n | win_rate_bps | median_wealth | mean_wealth | median_cash_low | price_range | bankrupt |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for a in result.aggregates:
        lines.append(
            f"| {a.policy_id} | {a.n} | {a.win_rate_bps} | {a.median_wealth} | {a.mean_wealth} | {a.median_cash_low} | {a.price_min}-{a.price_max} | {a.bankrupt_count} |"
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
        f"Hold-not-top gate (cash rank ≥3 intentional, ≥2×5% beats): {result.hold_not_top_reason} — {'PASS' if result.hold_not_top_gate_pass else 'FAIL'}"
    )
    lines.append(f"Price gate ([2000,9000]): {'PASS' if result.price_gate_pass else 'FAIL'}")
    lines.append(f"Negativity gate (no <0): {'PASS' if result.negativity_gate_pass else 'FAIL'}")
    lines.append(
        f"Route incremental: trade {result.trade_wealth} vs without {result.trade_without_route_wealth} → {result.route_incremental_value} ({result.route_incremental_value_bps_of_cost} bps of {ROUTE_ESTABLISH_COST} cost)"
    )
    lines.append(f"Tied best count: {result.tied_best_count}")
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
            "overall_median": result.overall_median,
        },
        "gates": {
            "dominant_pass": result.dominant_gate_pass,
            "dead_pass": result.dead_gate_pass,
            "price_pass": result.price_gate_pass,
            "negativity_pass": result.negativity_gate_pass,
            "hold_not_top_pass": result.hold_not_top_gate_pass,
            "median_ratio_bps": result.median_ratio_bps,
            "dominant_reason": result.dominant_reason,
            "dead_reason": result.dead_reason,
            "hold_not_top_reason": result.hold_not_top_reason,
            "trade_wealth": result.trade_wealth,
            "trade_without_route_wealth": result.trade_without_route_wealth,
            "route_incremental_value": result.route_incremental_value,
            "route_incremental_value_bps_of_cost": result.route_incremental_value_bps_of_cost,
            "tied_best_count": result.tied_best_count,
        },
        "per_seed": [r.model_dump() for r in result.per_seed],
    }
    return json.dumps(data, sort_keys=True, indent=2)
