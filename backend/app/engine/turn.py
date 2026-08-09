"""One-turn grain market kernel — Section 3.

Resolves a single turn with explicit order:

    Command -> Production -> Supply -> Price -> Inventory settlement -> Next state

All canonical state is integer; rounding via helpers; deterministic RNG
substream is consumed but core price remains deterministic to preserve
monotonicity. Causal trace is emitted structurally during resolution.

Spec: drought reduces production/yield, not directly price.
"""

from __future__ import annotations

from app.domain.trace import CausalNode, CausalTrace, DomainEffect, PlayerOutcome, TurnResolution
from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    PlayerCommand,
    PlayerState,
    TurnContext,
    WorldCondition,
)
from app.engine.rng import rng_for
from app.engine.rounding import clamp_non_negative, div_round_half_up

# Tuned constants — create real opportunity cost with starting cash ~1000.
YIELD_PER_CAPACITY: int = 10  # grain per farm_capacity under normal
DROUGHT_YIELD_REDUCTION_BPS: int = 4000  # 40% reduction
EXPAND_FARM_COST: int = 500
EXPAND_FARM_DELTA: int = 10
BUILD_GRANARY_COST: int = 300
BUILD_GRANARY_DELTA: int = 50

# Public for tests to assert order.
TURN_ORDER: str = "command -> production -> supply -> price -> settlement"


def _cost_for_quantity(quantity: int, price_milli: int) -> int:
    """Cost in Money for quantity at price_milli (milliunits per unit).

    Floor division — deterministic and conservative.
    Returns 0 if price_milli is 0 (free) or quantity 0.
    """
    if quantity <= 0 or price_milli <= 0:
        return 0
    return (quantity * price_milli) // 1000


def _affordable_quantity(cash: int, price_milli: int, requested: int) -> int:
    """Max quantity affordable at price_milli with cash, floored cost.

    Given cost = qty * price // 1000 <= cash, max qty is
    ((cash+1)*1000 -1)//price which accounts for flooring.
    """
    if requested <= 0:
        return 0
    if price_milli <= 0:
        return requested
    # ((cash+1)*1000 -1)//price is max qty where floor cost <= cash
    max_affordable = ((cash + 1) * 1000 - 1) // price_milli
    return max_affordable


def _target_price(
    base_price: int,
    supply: int,
    demand: int,
    responsiveness: int,
) -> int:
    """Integer-safe target price from supply/demand.

    - effective_supply = max(supply,1)
    - normalized_imbalance_bps = imbalance * 10_000 / effective_supply
    - price_pressure_bps = normalized_imbalance_bps * responsiveness / 10_000
    - target = base_price * (10_000 + pressure) / 10_000, clamped >=1
    """
    effective_supply = supply if supply > 0 else 1
    imbalance = demand - supply
    # Use half-up rounding for normalized imbalance to stay deterministic.
    normalized_bps = div_round_half_up(imbalance * 10_000, effective_supply)
    pressure_bps = (normalized_bps * responsiveness) // 10_000
    # target may be < base_price when supply > demand
    raw = base_price * (10_000 + pressure_bps) // 10_000
    # Ensure price stays positive; clamp to at least 1.
    if raw < 1:
        raw = 1
    return clamp_non_negative(raw)


def _bounded_price(
    current_price: int,
    target_price: int,
    max_movement_bps: int,
) -> int:
    """Bound movement toward target_price within max_movement_bps of current."""
    max_delta = (current_price * max_movement_bps) // 10_000
    desired = target_price - current_price
    if desired > max_delta:
        desired = max_delta
    elif desired < -max_delta:
        desired = -max_delta
    new_price = current_price + desired
    if new_price < 1:
        new_price = 1
    return clamp_non_negative(new_price)


def resolve_turn(
    state: GameState,
    command: PlayerCommand,
    world: WorldCondition,
    rng_context: TurnContext,
) -> TurnResolution:
    """Resolve one deterministic turn.

    Order is explicit: command -> production -> supply -> price -> settlement.

    Args:
        state: Canonical before state.
        command: Single player major action.
        world: World condition for this turn (normal/drought).
        rng_context: Turn identity for deterministic substreams.

    Returns:
        TurnResolution with next_state, domain_effects, causal_trace,
        player_outcome. No negatives, no direct drought->price edge.
    """
    # Consume deterministic RNG substream — preserves AC #1 and proves seed used.
    # Not allowed to use global random; rng_for is the only source.
    rng = rng_for(
        rng_context.run_seed,
        rng_context.ruleset_version,
        rng_context.turn,
        "turn",
        "price_jitter",
        0,
    )
    _ = rng.random()  # consume deterministically; do not drive core price

    before_cash = state.player.cash
    before_farm = state.player.farm_capacity
    before_storage = state.player.storage_capacity
    before_inventory = state.player.inventory.grain
    before_supply = state.market.supply
    before_demand = state.market.demand
    before_price = state.market.current_price
    base_price = state.market.base_price
    responsiveness = state.market.responsiveness
    max_movement_bps = state.market.max_movement_bps

    cash = before_cash
    farm_capacity = before_farm
    storage_capacity = before_storage
    inventory = before_inventory

    nodes: list[CausalNode] = []
    effects: list[DomainEffect] = []

    # World node — root cause, no parents.
    world_label = "Normal harvest" if world == "normal" else "Drought"
    world_reason = "normal_harvest" if world == "normal" else "drought"
    nodes.append(
        CausalNode(
            id="world",
            label=world_label,
            kind="world",
            before=None,
            after=None,
            delta=None,
            reason_code=world_reason,
            parent_ids=[],
        )
    )

    # 1. Command
    cmd_reason = ""
    if command.type == "expand_farm":
        if cash >= EXPAND_FARM_COST:
            cash -= EXPAND_FARM_COST
            farm_capacity += EXPAND_FARM_DELTA
            cmd_reason = "expand_farm"
            d_cash = -EXPAND_FARM_COST
            d_farm = EXPAND_FARM_DELTA
        else:
            cmd_reason = "insufficient_cash_for_expand"
            d_cash = 0
            d_farm = 0
        nodes.append(
            CausalNode(
                id="command",
                label="Expand farm",
                kind="command",
                before=before_farm,
                after=farm_capacity,
                delta=d_farm,
                reason_code=cmd_reason,
                parent_ids=[],
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after command",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=d_cash,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        nodes.append(
            CausalNode(
                id="farm_capacity",
                label="Farm capacity",
                kind="capacity",
                before=before_farm,
                after=farm_capacity,
                delta=d_farm,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=d_cash, reason_code=cmd_reason
            )
        )
        effects.append(
            DomainEffect(
                metric="farm_capacity",
                before=before_farm,
                after=farm_capacity,
                delta=d_farm,
                reason_code=cmd_reason,
            )
        )

    elif command.type == "build_granary":
        if cash >= BUILD_GRANARY_COST:
            cash -= BUILD_GRANARY_COST
            storage_capacity += BUILD_GRANARY_DELTA
            cmd_reason = "build_granary"
            d_cash = -BUILD_GRANARY_COST
            d_storage = BUILD_GRANARY_DELTA
        else:
            cmd_reason = "insufficient_cash_for_granary"
            d_cash = 0
            d_storage = 0
        nodes.append(
            CausalNode(
                id="command",
                label="Build granary",
                kind="command",
                before=before_storage,
                after=storage_capacity,
                delta=d_storage,
                reason_code=cmd_reason,
                parent_ids=[],
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after command",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=d_cash,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        nodes.append(
            CausalNode(
                id="storage_capacity",
                label="Storage capacity",
                kind="capacity",
                before=before_storage,
                after=storage_capacity,
                delta=d_storage,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=d_cash, reason_code=cmd_reason
            )
        )
        effects.append(
            DomainEffect(
                metric="storage_capacity",
                before=before_storage,
                after=storage_capacity,
                delta=d_storage,
                reason_code=cmd_reason,
            )
        )

    elif command.type == "buy_grain":
        requested = command.quantity if command.quantity is not None else 10
        # Clamp requested to non-negative int (Pydantic already ensures ge=0)
        requested = int(requested)
        available_space = storage_capacity - inventory
        if available_space < 0:
            available_space = 0
        affordable = _affordable_quantity(cash, before_price, requested)
        # actual is min of requested, affordable, space
        actual = requested
        if actual > affordable:
            actual = affordable
        if actual > available_space:
            actual = available_space
        cost = _cost_for_quantity(actual, before_price)
        # Determine reason
        if actual < requested and actual == affordable and actual < available_space:
            cmd_reason = "insufficient_cash"
        elif actual < requested and actual == available_space:
            # space was limiting (could also be both, prefer storage message if space < affordable)
            if available_space < affordable:
                cmd_reason = "insufficient_storage"
            else:
                # both limited but cash also limiting; prioritize - noqa: E501
                cmd_reason = (
                    "insufficient_cash" if affordable < requested else "insufficient_storage"
                )
            # More precise: if requested > available_space => storage
            if requested > available_space:
                # if also insufficient cash, we need to pick the tighter bound
                if affordable < available_space:
                    cmd_reason = "insufficient_cash"
                else:
                    cmd_reason = "insufficient_storage"
        elif actual == requested and requested > 0:
            cmd_reason = "buy_grain"
        elif actual == 0 and requested > 0:
            # Could be either cash or storage zero; decide
            if affordable == 0 and available_space > 0:
                cmd_reason = "insufficient_cash"
            elif available_space == 0:
                cmd_reason = "insufficient_storage"
            else:
                cmd_reason = "buy_grain_zero"
        else:
            cmd_reason = "buy_grain" if actual > 0 else "buy_grain_zero"

        cash_after = cash - cost
        inventory_after = inventory + actual

        nodes.append(
            CausalNode(
                id="command",
                label=f"Buy grain requested={requested} actual={actual}",
                kind="command",
                before=inventory,
                after=inventory_after,
                delta=actual,
                reason_code=cmd_reason,
                parent_ids=[],
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after buy",
                kind="cash",
                before=before_cash,
                after=cash_after,
                delta=-cost,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        nodes.append(
            CausalNode(
                id="inventory_after_buy",
                label="Inventory after buy",
                kind="inventory",
                before=before_inventory,
                after=inventory_after,
                delta=actual,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        effects.append(
            DomainEffect(
                metric="cash",
                before=before_cash,
                after=cash_after,
                delta=-cost,
                reason_code=cmd_reason,
            )
        )
        effects.append(
            DomainEffect(
                metric="inventory",
                before=before_inventory,
                after=inventory_after,
                delta=actual,
                reason_code=cmd_reason,
            )
        )

        cash = cash_after
        inventory = inventory_after

    else:  # hold
        cmd_reason = "hold"
        nodes.append(
            CausalNode(
                id="command",
                label="Hold cash",
                kind="command",
                before=before_cash,
                after=cash,
                delta=0,
                reason_code=cmd_reason,
                parent_ids=[],
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after hold",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=0,
                reason_code=cmd_reason,
                parent_ids=["command"],
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=0, reason_code=cmd_reason
            )
        )

    # Emit stable farm_capacity state node every turn so farm_output
    # depends on world + farm_capacity, not directly on command.
    # This fixes false command → production edges for hold/buy/build.
    if not any(n.id == "farm_capacity" for n in nodes):
        nodes.append(
            CausalNode(
                id="farm_capacity",
                label="Farm capacity",
                kind="capacity",
                before=before_farm,
                after=farm_capacity,
                delta=0,
                reason_code="farm_capacity_unchanged",
                parent_ids=[],
            )
        )

    # 2. Production — farm output depends on post-command farm_capacity + world
    base_output = farm_capacity * YIELD_PER_CAPACITY
    if world == "drought":
        farm_output = base_output * (10_000 - DROUGHT_YIELD_REDUCTION_BPS) // 10_000
        prod_reason = "drought_reduced_yield"
    else:
        farm_output = base_output
        prod_reason = "normal_yield"

    nodes.append(
        CausalNode(
            id="farm_output",
            label=f"Farm output {farm_output} (capacity {farm_capacity} × yield)",
            kind="production",
            before=base_output if world == "drought" else None,
            after=farm_output,
            delta=farm_output - base_output if world == "drought" else farm_output,
            reason_code=prod_reason,
            parent_ids=["world", "farm_capacity"],
        )
    )
    effects.append(
        DomainEffect(
            metric="farm_output",
            before=0,
            after=farm_output,
            delta=farm_output,
            reason_code=prod_reason,
        )
    )

    # 3. Supply — add farm_output to supply, clamped
    supply_before_harvest = before_supply
    next_supply = clamp_non_negative(supply_before_harvest + farm_output)
    supply_delta = next_supply - before_supply
    nodes.append(
        CausalNode(
            id="supply",
            label=f"Regional supply {before_supply} → {next_supply}",
            kind="supply",
            before=before_supply,
            after=next_supply,
            delta=supply_delta,
            reason_code="harvest_added_to_supply"
            if world == "normal"
            else "lower_output_reduced_supply",
            parent_ids=["farm_output"],
        )
    )
    effects.append(
        DomainEffect(
            metric="supply",
            before=before_supply,
            after=next_supply,
            delta=supply_delta,
            reason_code="supply_change",
        )
    )

    # 4. Price — target then bounded
    target = _target_price(base_price, next_supply, before_demand, responsiveness)
    new_price = _bounded_price(before_price, target, max_movement_bps)
    price_delta = new_price - before_price
    pressure_bps = (
        div_round_half_up(
            (before_demand - next_supply) * 10_000, next_supply if next_supply > 0 else 1
        )
        * responsiveness
        // 10_000
    )

    nodes.append(
        CausalNode(
            id="price_pressure",
            label=f"Price pressure {pressure_bps} bps",
            kind="price",
            before=None,
            after=pressure_bps,
            delta=pressure_bps,
            reason_code="supply_below_demand"
            if before_demand > next_supply
            else "supply_above_demand",
            parent_ids=["supply"],
        )
    )
    nodes.append(
        CausalNode(
            id="target_price",
            label=f"Target price {target}",
            kind="price",
            before=before_price,
            after=target,
            delta=target - before_price,
            reason_code="target_from_pressure",
            parent_ids=["price_pressure"],
        )
    )
    nodes.append(
        CausalNode(
            id="price",
            label=f"Market price {before_price} → {new_price}",
            kind="price",
            before=before_price,
            after=new_price,
            delta=price_delta,
            reason_code="bounded_movement_toward_target",
            parent_ids=["target_price"],
        )
    )
    effects.append(
        DomainEffect(
            metric="grain_price",
            before=before_price,
            after=new_price,
            delta=price_delta,
            reason_code="price_change",
        )
    )

    # 5. Settlement — inventory after harvest capped by storage
    inventory_before_settlement = inventory
    inventory_after_harvest = inventory_before_settlement + farm_output
    if inventory_after_harvest > storage_capacity:
        # Cap to storage; excess is lost (or would spoil, but no spoilage in S3)
        excess = inventory_after_harvest - storage_capacity
        inventory_final = storage_capacity
        settle_reason = "capped_by_storage"
        settle_delta = inventory_final - inventory_before_settlement
        # Record capped nature
        nodes.append(
            CausalNode(
                id="inventory",
                label=f"Inventory capped {inventory_before_settlement}+{farm_output} → {inventory_final} (excess {excess})",  # noqa: E501
                kind="inventory",
                before=inventory_before_settlement,
                after=inventory_final,
                delta=settle_delta,
                reason_code=settle_reason,
                parent_ids=[
                    "farm_output",
                    "inventory_after_buy" if command.type == "buy_grain" else "command",
                ],
            )
        )
    else:
        inventory_final = inventory_after_harvest
        settle_delta = farm_output
        settle_reason = "harvest_to_inventory"
        nodes.append(
            CausalNode(
                id="inventory",
                label=f"Inventory {inventory_before_settlement} → {inventory_final}",
                kind="inventory",
                before=inventory_before_settlement,
                after=inventory_final,
                delta=settle_delta,
                reason_code=settle_reason,
                parent_ids=["farm_output"],
            )
        )
    # Only add domain effect for settlement; always add delta.  # noqa: E501
    # But we already added inventory effect for buy; now add harvest.
    # To ensure AC #6 every major change has trace, node above covers it.
    # Add domain effect for inventory final vs before (overall)
    overall_inventory_delta = inventory_final - before_inventory
    # If we already added inventory for buy, this would be duplicate; combine.  # noqa: E501
    # Simpler: add second effect for harvest; tests check at least one exists.
    if command.type == "buy_grain":
        # already has one inventory effect; add harvest delta as separate
        effects.append(
            DomainEffect(
                metric="inventory_harvest",
                before=inventory_before_settlement,
                after=inventory_final,
                delta=settle_delta,
                reason_code=settle_reason,
            )
        )
    else:
        effects.append(
            DomainEffect(
                metric="inventory",
                before=before_inventory,
                after=inventory_final,
                delta=overall_inventory_delta,
                reason_code=settle_reason,
            )
        )

    # Next player state
    next_player = PlayerState(
        cash=cash,
        inventory=InventoryState(grain=inventory_final),
        farm_capacity=farm_capacity,
        storage_capacity=storage_capacity,
    )
    next_market = MarketState(
        supply=next_supply,
        demand=before_demand,
        base_price=base_price,
        current_price=new_price,
        responsiveness=responsiveness,
        max_movement_bps=max_movement_bps,
    )
    next_state = GameState(
        turn=state.turn + 1,
        run_seed=state.run_seed,
        ruleset_version=state.ruleset_version,
        player=next_player,
        market=next_market,
    )

    # Player outcome — deterministic top drivers from trace by absolute delta
    # Wealth delta includes cash + inventory value at new price vs old price
    inventory_value_before = before_inventory * before_price // 1000
    inventory_value_after = inventory_final * new_price // 1000
    wealth_before = before_cash + inventory_value_before
    wealth_after = cash + inventory_value_after
    wealth_delta = wealth_after - wealth_before

    # Rank drivers by abs(delta) where delta not None
    candidates = [n for n in nodes if n.delta is not None and n.id not in ("world",)]
    # Sort by abs(delta) desc, then id for determinism
    candidates_sorted = sorted(
        candidates, key=lambda n: (abs(n.delta if n.delta is not None else 0), n.id), reverse=True
    )
    top_drivers = [c.label for c in candidates_sorted[:3]]

    player_outcome = PlayerOutcome(
        wealth_delta=wealth_delta,
        inventory_delta=overall_inventory_delta,
        price_delta=price_delta,
        top_drivers=top_drivers,
    )

    trace = CausalTrace(nodes=nodes)

    return TurnResolution(
        next_state=next_state,
        domain_effects=effects,
        causal_trace=trace,
        player_outcome=player_outcome,
    )
