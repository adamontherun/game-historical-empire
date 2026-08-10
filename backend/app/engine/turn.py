"""One-turn grain market kernel — Sections 4–6, regional_output Section 9.

Resolves a single turn with explicit order:

    Command -> Production -> RegionalOutput -> HomeSupply -> RiverSupply -> HomePrice -> RiverPrice -> Settlement -> RouteSettlement -> Valuation

All canonical state is integer; rounding via helpers; deterministic RNG
substream is consumed but core price remains deterministic to preserve
monotonicity. Causal trace is emitted structurally during resolution.
Wealth is now part of the causal graph via exact decomposition:

    wealth_before = cash_before + value(inv_before, price_before_home)
    quantity_value_effect = value(inv_after, price_before_home) - value(inv_before, price_before_home)
                          = purchase + harvest + ship
    price_value_effect    = value(inv_after, price_after_home)  - value(inv_after, price_before_home)
    cash_effect           = cash_after - cash_before
    wealth_delta          = cash_effect + quantity_value_effect + price_value_effect

where value(qty, price_milli) = qty * price_milli // 1000.
Story drivers are exact partitions of wealth_delta ranked by wealth-bps.
Section 5 adds: Home Valley (existing market) + River Town (river_market)
+ River Route (route) with transport cost / capacity / reliability.
Ship trade is settlement after harvest, valued at river price.

Supply semantics (Section 6, revised Section 9): MarketState.supply is a regional
market-availability signal/index at the start of the turn. Home Valley signal evolves as
signal_next = max(0, signal + regional_output_after_world + farm_output - demand),
where regional_output_after_world reuses the same drought reduction (DROUGHT_YIELD_REDUCTION_BPS)
as the player's farm via actor. Price is set on signal_next via _target_price
with effective_supply guard. The same farm_output also enters player inventory;
for this prototype no conservation is implied between the regional signal and
player inventory (ownership deferred to Section 14). River Town signal remains stable (exogenous).

Spec: drought reduces production/yield, not directly price.
"""

from __future__ import annotations

from app.domain.pressure import PressureState
from app.domain.trace import (
    CausalNode,
    CausalTrace,
    DomainEffect,
    OutcomeDriver,
    PlayerOutcome,
    TurnResolution,
)
from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    PlayerCommand,
    PlayerState,
    TurnContext,
)
from app.engine.actor import (
    DROUGHT_YIELD_REDUCTION_BPS,  # noqa: F401  re-export for backward compat
    compute_farm_output,
    resolve_build_granary,
    resolve_buy,
    resolve_expand_farm,
    resolve_secure_route,
    resolve_sell,
    resolve_shipment,
    resolve_storage_settlement,
)
from app.engine.actor import (
    value_for as _value,
)
from app.engine.rng import rng_for
from app.engine.rounding import clamp_non_negative, div_round_half_up


def _regional_output_after_world(base: int, world: str) -> tuple[int, str]:
    """Non-player regional output after world effect — reuses same drought primitive."""
    if world == "drought":
        after = base * (10_000 - DROUGHT_YIELD_REDUCTION_BPS) // 10_000
        return after, "drought_reduced_yield"
    return base, "normal_yield"


# Public for tests to assert order.
TURN_ORDER: str = "pressure_stage -> world -> command -> production -> regional_output -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation"


def _target_price(
    base_price: int,
    supply: int,
    demand: int,
    responsiveness: int,
) -> int:
    """Integer-safe target price from supply/demand."""
    effective_supply = supply if supply > 0 else 1
    imbalance = demand - supply
    normalized_bps = div_round_half_up(imbalance * 10_000, effective_supply)
    pressure_bps = (normalized_bps * responsiveness) // 10_000
    raw = base_price * (10_000 + pressure_bps) // 10_000
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
    pressure: PressureState,
    rng_context: TurnContext,
) -> TurnResolution:
    """Resolve one deterministic turn.

    Order is explicit: pressure_stage -> world -> command -> production -> regional_output -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation.

    Args:
        state: Canonical before state (includes home market, river market, route).
        command: Single player major action (now includes secure_route/ship_grain).
        pressure: Pressure state for this turn (world derived as pressure.world).
        rng_context: Turn identity for deterministic substreams — must equal state context.

    Returns:
        TurnResolution with next_state, domain_effects, causal_trace, player_outcome.
        Wealth is part of the graph via exact decomposition; drivers are exact partitions.
    """
    # RNG ownership validation — must equal state's context
    expected = state.to_turn_context()
    if rng_context != expected:
        raise ValueError(f"rng_context {rng_context} != state context {expected}")
    rng = rng_for(
        expected.run_seed,
        expected.ruleset_version,
        expected.turn,
        "turn",
        "price_jitter",
        0,
    )
    _ = rng.random()  # consume deterministically; do not drive core price
    # Also consume route substream deterministically
    rng_route = rng_for(
        expected.run_seed,
        expected.ruleset_version,
        expected.turn,
        "route",
        "river_route",
        0,
    )
    _ = rng_route.random()

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

    # River market before
    before_river_supply = state.river_market.supply
    before_river_demand = state.river_market.demand
    before_river_price = state.river_market.current_price
    river_base_price = state.river_market.base_price
    river_responsiveness = state.river_market.responsiveness
    river_max_movement_bps = state.river_market.max_movement_bps

    # Route before
    before_route = state.route
    route_capacity = before_route.capacity
    route_reliability_bps = before_route.reliability_bps
    transport_cost_per_unit = before_route.transport_cost_per_unit
    route_established_before = before_route.established

    # Mutable working copies
    cash = before_cash
    farm_capacity = before_farm
    storage_capacity = before_storage
    inventory = before_inventory
    route_established = route_established_before
    before_finished = state.player.inventory.finished_goods
    before_labour = state.player.skilled_labour
    finished_inventory = before_finished
    skilled_labour = before_labour

    # Ship tracking
    ship_requested: int | None = None
    ship_effective: int = 0
    ship_delivered: int = 0
    ship_revenue: int = 0
    ship_cost: int = 0
    ship_reason: str = ""
    trade_cash: int = 0  # part of cash_effect from ship
    arbitrage_margin: int = 0  # resolved-price arbitrage: river - transport - new_home

    nodes: list[CausalNode] = []
    effects: list[DomainEffect] = []

    # Pressure stage — single source of truth (F3): reason_code is causal_source_id directly
    # Label is stage-derived causal description, not presentation title (G5)
    _STAGE_LABEL: dict[str, str] = {
        "normal": "Normal conditions",
        "early_dry": "Early dry conditions",
        "worsening_dry": "Worsening dry conditions",
        "drought": "Drought conditions",
        "aftermath": "Aftermath conditions",
    }
    world = pressure.world
    nodes.append(
        CausalNode(
            id="pressure_stage",
            label=_STAGE_LABEL.get(pressure.stage, pressure.stage),
            kind="pressure",
            before=None,
            after=None,
            delta=None,
            reason_code=pressure.causal_source_id,
            parent_ids=(),
        )
    )

    # World node — child of pressure_stage (systemic chain)
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
            parent_ids=("pressure_stage",),
        )
    )

    # 1. Command
    cmd_reason = ""
    if command.type == "expand_farm":
        cash_before_cmd = cash
        cash, farm_capacity, d_farm, cmd_reason = resolve_expand_farm(
            cash=cash, farm_capacity=farm_capacity
        )
        d_cash = cash - cash_before_cmd
        nodes.append(
            CausalNode(
                id="command",
                label="Expand farm",
                kind="command",
                before=before_farm,
                after=farm_capacity,
                delta=d_farm,
                reason_code=cmd_reason,
                parent_ids=(),
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
                parent_ids=("command",),
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
                parent_ids=("command",),
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
        cash_before_cmd = cash
        cash, storage_capacity, d_storage, cmd_reason = resolve_build_granary(
            cash=cash, storage_capacity=storage_capacity
        )
        d_cash = cash - cash_before_cmd
        nodes.append(
            CausalNode(
                id="command",
                label="Build granary",
                kind="command",
                before=before_storage,
                after=storage_capacity,
                delta=d_storage,
                reason_code=cmd_reason,
                parent_ids=(),
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
                parent_ids=("command",),
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
                parent_ids=("command",),
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
        requested = int(requested)
        cash_after, inventory_after, actual, cost, cmd_reason = resolve_buy(
            cash=cash,
            price_milli=before_price,
            storage_capacity=storage_capacity,
            inventory=inventory,
            requested=requested,
        )

        nodes.append(
            CausalNode(
                id="command",
                label=f"Buy grain requested={requested} actual={actual}",
                kind="command",
                before=inventory,
                after=inventory_after,
                delta=actual,
                reason_code=cmd_reason,
                parent_ids=(),
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
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="inventory_after_command",
                label="Inventory after buy",
                kind="inventory",
                before=before_inventory,
                after=inventory_after,
                delta=actual,
                reason_code=cmd_reason,
                parent_ids=("command",),
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

    elif command.type == "sell_grain":
        requested = command.quantity if command.quantity is not None else 10
        requested = int(requested)
        cash_after, inventory_after, actual, revenue, cmd_reason = resolve_sell(
            cash=cash,
            price_milli=before_price,
            inventory=inventory,
            requested=requested,
        )

        nodes.append(
            CausalNode(
                id="command",
                label=f"Sell grain requested={requested} actual={actual}",
                kind="command",
                before=inventory,
                after=inventory_after,
                delta=-actual,
                reason_code=cmd_reason,
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after sell",
                kind="cash",
                before=before_cash,
                after=cash_after,
                delta=revenue,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="inventory_after_command",
                label="Inventory after sell",
                kind="inventory",
                before=before_inventory,
                after=inventory_after,
                delta=-actual,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        effects.append(
            DomainEffect(
                metric="cash",
                before=before_cash,
                after=cash_after,
                delta=revenue,
                reason_code=cmd_reason,
            )
        )
        effects.append(
            DomainEffect(
                metric="inventory",
                before=before_inventory,
                after=inventory_after,
                delta=-actual,
                reason_code=cmd_reason,
            )
        )

        cash = cash_after
        inventory = inventory_after

    elif command.type == "secure_route":
        cash_before_cmd = cash
        cash, route_established, _d_route, cmd_reason = resolve_secure_route(
            cash=cash, route_established=route_established_before
        )
        # For this branch route_established_before is the before, but helper already handles
        # route_established variable now holds after value
        d_cash = cash - cash_before_cmd
        nodes.append(
            CausalNode(
                id="command",
                label="Secure river route",
                kind="command",
                before=1 if route_established_before else 0,
                after=1 if route_established else 0,
                delta=1 if route_established and not route_established_before else 0,
                reason_code=cmd_reason,
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after secure route",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=d_cash,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        # Also emit a route establishment node for trace clarity
        nodes.append(
            CausalNode(
                id="route_established",
                label="Route established" if route_established else "Route not established",
                kind="route",
                before=1 if route_established_before else 0,
                after=1 if route_established else 0,
                delta=1 if route_established and not route_established_before else 0,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=d_cash, reason_code=cmd_reason
            )
        )
        effects.append(
            DomainEffect(
                metric="route_established",
                before=1 if route_established_before else 0,
                after=1 if route_established else 0,
                delta=1 if route_established and not route_established_before else 0,
                reason_code=cmd_reason,
            )
        )

    elif command.type == "ship_grain":
        requested = command.quantity if command.quantity is not None else 10
        requested = int(requested)
        ship_requested = requested
        if not route_established_before:
            cmd_reason = "no_route_access"
            ship_reason = "no_route_access"
            ship_effective = 0
            ship_delivered = 0
            ship_revenue = 0
            ship_cost = 0
        else:
            # Defer full clamping until settlement when harvest known;
            # For command node, just record requested.
            cmd_reason = "ship_grain_planned"
            ship_reason = "ship_grain_planned"
            # Keep effective 0 for now; will compute at settlement.
            ship_effective = 0
        nodes.append(
            CausalNode(
                id="command",
                label=f"Ship grain requested={requested} route={'established' if route_established_before else 'not_established'}",
                kind="command",
                before=before_inventory,
                after=before_inventory,  # inventory not yet moved
                delta=0,
                reason_code=cmd_reason,
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after ship command (deferred)",
                kind="cash",
                before=before_cash,
                after=cash,  # unchanged at command phase
                delta=0,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        # Emit a placeholder shipment node with 0 delta; real settlement will add the effective node later.
        # For now, keep effects with 0 delta; settlement will add real effects.
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=0, reason_code=cmd_reason
            )
        )
        # Keep inventory effect 0 at command phase
        effects.append(
            DomainEffect(
                metric="shipment_requested",
                before=0,
                after=requested,
                delta=requested,
                reason_code=cmd_reason,
            )
        )

    elif command.type == "craft_goods":
        requested = command.quantity if command.quantity is not None else 10
        requested = int(requested)
        # Granary does NOT improve conversion — old mastery does not transfer.
        # Keep efficiency uniform 3/10 for all; labour count is the lever (river_contracts gives +2)
        eff_num = 3
        eff_den = 10
        # Use shared primitive
        from app.engine.actor import resolve_craft as _resolve_craft

        grain_after_tmp, _fin_prod, actual_grain, finished_out, cmd_reason = _resolve_craft(
            grain_inventory=inventory,
            skilled_labour=skilled_labour,
            requested=requested,
            efficiency_num=eff_num,
            efficiency_den=eff_den,
        )
        # finished_out already computed; update working copies
        d_grain = grain_after_tmp - inventory
        inventory = grain_after_tmp
        finished_inventory = before_finished + finished_out
        nodes.append(
            CausalNode(
                id="command",
                label=f"Craft goods requested={requested} actual={actual_grain} finished={finished_out}",
                kind="command",
                before=before_inventory,
                after=inventory,
                delta=-actual_grain,
                reason_code=cmd_reason,
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after craft (no cash cost)",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=0,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="labour_capacity",
                label=f"Labour capacity {skilled_labour}×10={skilled_labour * 10}",
                kind="labour",
                before=before_labour,
                after=skilled_labour,
                delta=0,
                reason_code="labour_capacity_unchanged"
                if cmd_reason != "no_skilled_labour"
                else "no_skilled_labour",
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="craft_conversion",
                label=f"Craft {actual_grain} grain → {finished_out} finished",
                kind="craft",
                before=before_inventory,
                after=inventory,
                delta=-actual_grain,
                reason_code=cmd_reason,
                parent_ids=("command", "labour_capacity"),
            )
        )
        nodes.append(
            CausalNode(
                id="finished_inventory",
                label=f"Finished inventory {before_finished} → {finished_inventory}",
                kind="finished_inventory",
                before=before_finished,
                after=finished_inventory,
                delta=finished_out,
                reason_code=cmd_reason,
                parent_ids=("craft_conversion",),
            )
        )
        effects.append(
            DomainEffect(
                metric="grain_inventory",
                before=before_inventory,
                after=inventory,
                delta=d_grain,
                reason_code=cmd_reason,
            )
        )
        effects.append(
            DomainEffect(
                metric="finished_goods",
                before=before_finished,
                after=finished_inventory,
                delta=finished_out,
                reason_code=cmd_reason,
            )
        )

    elif command.type == "sell_finished_goods":
        requested = command.quantity if command.quantity is not None else 10
        requested = int(requested)
        has_river = "river_contracts" in state.legacies
        from app.engine.actor import (
            FINISHED_GOODS_PRICE,
            FINISHED_GOODS_PRICE_RIVER_EXTRA,
            resolve_sell_finished,
        )

        price = FINISHED_GOODS_PRICE + (FINISHED_GOODS_PRICE_RIVER_EXTRA if has_river else 0)
        cash_after, finished_after, actual, revenue, cmd_reason = resolve_sell_finished(
            cash=cash, finished_inventory=finished_inventory, price_milli=price, requested=requested
        )
        d_cash = cash_after - cash
        cash = cash_after
        finished_inventory = finished_after
        nodes.append(
            CausalNode(
                id="command",
                label=f"Sell finished requested={requested} actual={actual}",
                kind="command",
                before=before_finished,
                after=finished_inventory,
                delta=-actual,
                reason_code=cmd_reason,
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after sell finished",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=d_cash,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="finished_price",
                label=f"Finished price {price}",
                kind="finished_price",
                before=price,
                after=price,
                delta=0,
                reason_code="finished_price_river_extra" if has_river else "finished_price_stable",
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="finished_inventory",
                label=f"Finished inventory {before_finished} → {finished_inventory}",
                kind="finished_inventory",
                before=before_finished,
                after=finished_inventory,
                delta=-actual,
                reason_code=cmd_reason,
                parent_ids=("command", "finished_price"),
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=d_cash, reason_code=cmd_reason
            )
        )
        effects.append(
            DomainEffect(
                metric="finished_goods",
                before=before_finished,
                after=finished_inventory,
                delta=-actual,
                reason_code=cmd_reason,
            )
        )

    elif command.type == "hire_labour":
        has_reputation = "crisis_reputation" in state.legacies
        from app.engine.actor import resolve_hire_labour

        cash_after, labour_after, d_labour, cmd_reason = resolve_hire_labour(
            cash=cash, skilled_labour=skilled_labour, has_reputation=has_reputation
        )
        d_cash = cash_after - cash
        cash = cash_after
        skilled_labour = labour_after
        nodes.append(
            CausalNode(
                id="command",
                label="Hire labour",
                kind="command",
                before=before_labour,
                after=skilled_labour,
                delta=d_labour,
                reason_code=cmd_reason,
                parent_ids=(),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_command",
                label="Cash after hire",
                kind="cash",
                before=before_cash,
                after=cash,
                delta=d_cash,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="hire_labour",
                label=f"Hire labour {before_labour} → {skilled_labour}",
                kind="labour",
                before=before_labour,
                after=skilled_labour,
                delta=d_labour,
                reason_code=cmd_reason,
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="labour_capacity",
                label=f"Labour capacity {skilled_labour}×10={skilled_labour * 10}",
                kind="labour",
                before=before_labour,
                after=skilled_labour,
                delta=d_labour,
                reason_code=cmd_reason,
                parent_ids=("hire_labour",),
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=d_cash, reason_code=cmd_reason
            )
        )
        effects.append(
            DomainEffect(
                metric="skilled_labour",
                before=before_labour,
                after=skilled_labour,
                delta=d_labour,
                reason_code=cmd_reason,
            )
        )

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
                parent_ids=(),
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
                parent_ids=("command",),
            )
        )
        effects.append(
            DomainEffect(
                metric="cash", before=before_cash, after=cash, delta=0, reason_code=cmd_reason
            )
        )

    # Emit stable farm_capacity state node every turn so
    # farm_output depends on world + farm_capacity
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
                parent_ids=(),
            )
        )
    # Emit stable storage_capacity state node every turn so
    # inventory depends on farm_output + storage_capacity
    if not any(n.id == "storage_capacity" for n in nodes):
        nodes.append(
            CausalNode(
                id="storage_capacity",
                label="Storage capacity",
                kind="capacity",
                before=before_storage,
                after=storage_capacity,
                delta=0,
                reason_code="storage_capacity_unchanged",
                parent_ids=(),
            )
        )
    # Emit stable route nodes every turn for observability
    if not any(n.id == "route_capacity" for n in nodes):
        nodes.append(
            CausalNode(
                id="route_capacity",
                label=f"Route capacity {route_capacity}",
                kind="route",
                before=route_capacity,
                after=route_capacity,
                delta=0,
                reason_code="route_capacity_unchanged",
                parent_ids=(),
            )
        )
    if not any(n.id == "route_cost_per_unit" for n in nodes):
        nodes.append(
            CausalNode(
                id="route_cost_per_unit",
                label=f"Route transport cost {transport_cost_per_unit}",
                kind="route",
                before=transport_cost_per_unit,
                after=transport_cost_per_unit,
                delta=0,
                reason_code="route_cost_unchanged",
                parent_ids=(),
            )
        )
    if not any(n.id == "route_reliability" for n in nodes):
        nodes.append(
            CausalNode(
                id="route_reliability",
                label=f"Route reliability {route_reliability_bps} bps",
                kind="route",
                before=route_reliability_bps,
                after=route_reliability_bps,
                delta=0,
                reason_code="route_reliability_unchanged",
                parent_ids=(),
            )
        )
    # Also ensure route_established stable node if not already from secure_route
    if not any(n.id == "route_established" for n in nodes):
        nodes.append(
            CausalNode(
                id="route_established",
                label="Route established" if route_established else "Route not established",
                kind="route",
                before=1 if route_established_before else 0,
                after=1 if route_established else 0,
                delta=0,
                reason_code="route_established_unchanged",
                parent_ids=(),
            )
        )

    # Emit demand signal nodes (stable inputs) — Section 6 causal graph fix
    # Home demand directly causes availability signal changes and price pressure
    nodes.append(
        CausalNode(
            id="demand",
            label=f"Home demand {before_demand}",
            kind="demand",
            before=before_demand,
            after=before_demand,
            delta=0,
            reason_code="demand_stable",
            parent_ids=(),
        )
    )
    nodes.append(
        CausalNode(
            id="home_demand",
            label=f"Home Valley demand {before_demand}",
            kind="demand",
            before=before_demand,
            after=before_demand,
            delta=0,
            reason_code="demand_stable",
            parent_ids=(),
        )
    )
    # Section 13 — epilogue demand shift: raw demand falls, urban demand for finished goods emerges
    # Determine effective demand for supply calc — prototype may have already mutated state's demand,
    # but also support legacy disable flag via GameState.legacies containing "disable_demand_shift"
    effective_demand = before_demand
    demand_shift_reason = "demand_stable"
    if state.turn >= 5:
        # Check if demand shift is disabled via legacy flag (Control C)
        if "disable_demand_shift" not in state.legacies:
            from app.engine.actor import EPILOGUE_RAW_DEMAND

            idx = state.turn - 5
            if 0 <= idx < len(EPILOGUE_RAW_DEMAND):
                effective_demand = EPILOGUE_RAW_DEMAND[idx]
                demand_shift_reason = "epilogue_demand_shift"
        # Emit urban demand node (finished goods buyer) — every epilogue turn
        from app.engine.actor import FINISHED_GOODS_PRICE

        finished_price_node = FINISHED_GOODS_PRICE + (
            800 if "river_contracts" in state.legacies else 0
        )
        nodes.append(
            CausalNode(
                id="urban_demand",
                label=f"Urban demand for finished goods — price {finished_price_node}",
                kind="urban_demand",
                before=410,
                after=effective_demand,
                delta=effective_demand - 410
                if demand_shift_reason == "epilogue_demand_shift"
                else 0,
                reason_code="urban_demand_high"
                if demand_shift_reason == "epilogue_demand_shift"
                else "demand_stable",
                parent_ids=("pressure_stage",),
            )
        )
        # Raw demand shift node — explains why grain sells badly
        if demand_shift_reason == "epilogue_demand_shift":
            nodes.append(
                CausalNode(
                    id="raw_demand_shift",
                    label=f"Raw grain demand falls {before_demand}→{effective_demand}",
                    kind="demand",
                    before=before_demand,
                    after=effective_demand,
                    delta=effective_demand - before_demand,
                    reason_code="urbanization_reduces_grain_demand",
                    parent_ids=("urban_demand",),
                )
            )

    # 2. Production — farm output via shared primitive
    farm_output, base_output, prod_reason = compute_farm_output(farm_capacity, world)

    nodes.append(
        CausalNode(
            id="farm_output",
            label=f"Farm output {farm_output} (capacity {farm_capacity} × yield)",
            kind="production",
            before=base_output if world == "drought" else None,
            after=farm_output,
            delta=farm_output - base_output if world == "drought" else farm_output,
            reason_code=prod_reason,
            parent_ids=("world", "farm_capacity"),
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

    # 2b. Regional output — non-player, same drought reduction
    regional_base = state.market.regional_output
    regional_after, regional_reason = _regional_output_after_world(regional_base, world)
    nodes.append(
        CausalNode(
            id="regional_output",
            label=f"Regional output {regional_after} (base {regional_base})",
            kind="production",
            before=regional_base if world == "drought" else None,
            after=regional_after,
            delta=regional_after - regional_base if world == "drought" else regional_after,
            reason_code=regional_reason,
            parent_ids=("world",),
        )
    )
    effects.append(
        DomainEffect(
            metric="regional_output",
            before=regional_base if world == "drought" else 0,
            after=regional_after,
            delta=regional_after - regional_base if world == "drought" else regional_after,
            reason_code=regional_reason,
        )
    )

    # 3. Home Supply — availability signal drained by demand (Section 9: includes regional)
    # signal_next = max(0, signal + regional_after + farm_output - demand)
    # For epilogue turns, demand may have shifted via effective_demand
    supply_before_harvest = before_supply
    # effective_demand is defined above for epilogue; fallback to before_demand for earlier turns
    try:
        _eff_demand = effective_demand  # type: ignore[possibly-undefined]
    except NameError:
        _eff_demand = before_demand
    next_supply = clamp_non_negative(
        supply_before_harvest + regional_after + farm_output - _eff_demand
    )
    supply_delta = next_supply - before_supply
    # Reason reflects whether signal grew (surplus) or shrank (shortage)
    if next_supply > before_supply:
        supply_reason = "harvest_added_to_availability"
    elif next_supply < before_supply:
        supply_reason = "availability_drained_by_demand"
    else:
        supply_reason = "availability_unchanged"
    if world == "drought" and next_supply < before_supply:
        supply_reason = "drought_reduced_availability"
    nodes.append(
        CausalNode(
            id="supply",
            label=f"Regional availability {before_supply}+{regional_after}+{farm_output}-{before_demand}→{next_supply}",
            kind="supply",
            before=before_supply,
            after=next_supply,
            delta=supply_delta,
            reason_code=supply_reason,
            parent_ids=("regional_output", "farm_output", "demand"),
        )
    )
    # Also emit alias home_supply for clarity
    nodes.append(
        CausalNode(
            id="home_supply",
            label=f"Home Valley availability {before_supply}+{regional_after}+{farm_output}-{before_demand}→{next_supply}",
            kind="supply",
            before=before_supply,
            after=next_supply,
            delta=supply_delta,
            reason_code=supply_reason,
            parent_ids=("regional_output", "farm_output", "home_demand"),
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
    effects.append(
        DomainEffect(
            metric="home_supply",
            before=before_supply,
            after=next_supply,
            delta=supply_delta,
            reason_code="supply_change",
        )
    )

    # 3b. River Supply — stable, not affected by home farm output (River not farm center)
    river_supply_next = before_river_supply
    river_supply_delta = 0
    nodes.append(
        CausalNode(
            id="river_supply",
            label=f"River Town supply {before_river_supply} → {river_supply_next}",
            kind="river_supply",
            before=before_river_supply,
            after=river_supply_next,
            delta=river_supply_delta,
            reason_code="river_supply_stable",
            parent_ids=("world",),
        )
    )
    effects.append(
        DomainEffect(
            metric="river_supply",
            before=before_river_supply,
            after=river_supply_next,
            delta=river_supply_delta,
            reason_code="river_supply_stable",
        )
    )

    # 4. Home Price — target then bounded
    # For epilogue, use effective demand (urban shift) for price pressure
    try:
        _price_demand = _eff_demand  # type: ignore[name-defined]
    except NameError:
        _price_demand = before_demand
    target = _target_price(base_price, next_supply, _price_demand, responsiveness)
    new_price = _bounded_price(before_price, target, max_movement_bps)
    price_delta = new_price - before_price
    pressure_bps = (
        div_round_half_up(
            (_price_demand - next_supply) * 10_000, next_supply if next_supply > 0 else 1
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
            parent_ids=("supply", "demand"),
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
            parent_ids=("price_pressure",),
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
            reason_code="bounded_movement_toward_target"
            if state.turn < 5 or "disable_demand_shift" in state.legacies
            else "raw_price_collapse_in_city",
            parent_ids=("target_price",),
        )
    )
    # Home aliases for clarity
    nodes.append(
        CausalNode(
            id="home_price_pressure",
            label=f"Home price pressure {pressure_bps} bps",
            kind="price",
            before=None,
            after=pressure_bps,
            delta=pressure_bps,
            reason_code="supply_below_demand"
            if before_demand > next_supply
            else "supply_above_demand",
            parent_ids=("home_supply", "home_demand"),
        )
    )
    nodes.append(
        CausalNode(
            id="home_target_price",
            label=f"Home target price {target}",
            kind="price",
            before=before_price,
            after=target,
            delta=target - before_price,
            reason_code="target_from_pressure",
            parent_ids=("home_price_pressure",),
        )
    )
    nodes.append(
        CausalNode(
            id="home_price",
            label=f"Home price {before_price} → {new_price}",
            kind="price",
            before=before_price,
            after=new_price,
            delta=price_delta,
            reason_code="bounded_movement_toward_target",
            parent_ids=("home_target_price",),
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
    effects.append(
        DomainEffect(
            metric="home_price",
            before=before_price,
            after=new_price,
            delta=price_delta,
            reason_code="price_change",
        )
    )

    # 4b. River Price — target then bounded using river supply/demand
    river_target = _target_price(
        river_base_price, river_supply_next, before_river_demand, river_responsiveness
    )
    river_new_price = _bounded_price(before_river_price, river_target, river_max_movement_bps)
    river_price_delta = river_new_price - before_river_price
    river_pressure_bps = (
        div_round_half_up(
            (before_river_demand - river_supply_next) * 10_000,
            river_supply_next if river_supply_next > 0 else 1,
        )
        * river_responsiveness
        // 10_000
    )
    nodes.append(
        CausalNode(
            id="river_price_pressure",
            label=f"River price pressure {river_pressure_bps} bps",
            kind="river_price",
            before=None,
            after=river_pressure_bps,
            delta=river_pressure_bps,
            reason_code="supply_below_demand"
            if before_river_demand > river_supply_next
            else "supply_above_demand",
            parent_ids=("river_supply",),
        )
    )
    nodes.append(
        CausalNode(
            id="river_target_price",
            label=f"River target price {river_target}",
            kind="river_price",
            before=before_river_price,
            after=river_target,
            delta=river_target - before_river_price,
            reason_code="target_from_pressure",
            parent_ids=("river_price_pressure",),
        )
    )
    nodes.append(
        CausalNode(
            id="river_price",
            label=f"River Town price {before_river_price} → {river_new_price}",
            kind="river_price",
            before=before_river_price,
            after=river_new_price,
            delta=river_price_delta,
            reason_code="bounded_movement_toward_target",
            parent_ids=("river_target_price",),
        )
    )
    effects.append(
        DomainEffect(
            metric="river_grain_price",
            before=before_river_price,
            after=river_new_price,
            delta=river_price_delta,
            reason_code="river_price_change",
        )
    )

    # 5. Settlement — inventory after harvest capped by storage (via shared primitive)
    inventory_before_settlement = inventory
    inventory_final_pre_ship, settle_delta, settle_reason = resolve_storage_settlement(
        inventory_before=inventory_before_settlement,
        farm_output=farm_output,
        storage_capacity=storage_capacity,
    )
    # Reconstruct label details for trace (excess) while preserving shared math
    if settle_reason == "capped_by_storage":
        excess = inventory_before_settlement + farm_output - storage_capacity
        if command.type in ("buy_grain", "sell_grain"):
            inv_parents = ("farm_output", "storage_capacity", "inventory_after_command")
        else:
            inv_parents = ("farm_output", "storage_capacity")
        nodes.append(
            CausalNode(
                id="inventory",
                label=f"Inventory capped {inventory_before_settlement}+{farm_output} → {inventory_final_pre_ship} (excess {excess})",
                kind="inventory",
                before=inventory_before_settlement,
                after=inventory_final_pre_ship,
                delta=settle_delta,
                reason_code=settle_reason,
                parent_ids=inv_parents,
            )
        )
    else:
        # harvest_to_inventory
        if command.type in ("buy_grain", "sell_grain"):
            inv_parents = ("farm_output", "storage_capacity", "inventory_after_command")
        else:
            inv_parents = ("farm_output", "storage_capacity")
        nodes.append(
            CausalNode(
                id="inventory",
                label=f"Inventory {inventory_before_settlement} → {inventory_final_pre_ship}",
                kind="inventory",
                before=inventory_before_settlement,
                after=inventory_final_pre_ship,
                delta=settle_delta,
                reason_code=settle_reason,
                parent_ids=inv_parents,
            )
        )
    # Domain effects for settlement
    overall_inventory_delta_pre_ship = inventory_final_pre_ship - before_inventory
    if command.type in ("buy_grain", "sell_grain"):
        effects.append(
            DomainEffect(
                metric="inventory_harvest",
                before=inventory_before_settlement,
                after=inventory_final_pre_ship,
                delta=settle_delta,
                reason_code=settle_reason,
            )
        )
    else:
        effects.append(
            DomainEffect(
                metric="inventory",
                before=before_inventory,
                after=inventory_final_pre_ship,
                delta=overall_inventory_delta_pre_ship,
                reason_code=settle_reason,
            )
        )

    # 5b. Route settlement — ship execution (if requested)
    # inventory_final will be mutated if ship succeeds
    inventory_final = inventory_final_pre_ship
    # ship_quantity_value placeholder for valuation later; computed after we know effective
    ship_quantity_value_pre = 0  # will be computed
    # Track if ship was planned
    is_ship_command = command.type == "ship_grain"
    if is_ship_command:
        assert ship_requested is not None
        requested = ship_requested
        # ship_requested is set only for ship_grain; but if route not established before, it's blocked
        if not route_established_before:
            # Blocked: no movement
            ship_effective = 0
            ship_delivered = 0
            ship_revenue = 0
            ship_cost = 0
            ship_reason = "no_route_access"
            trade_cash = 0
            arbitrage_margin = 0
            ship_quantity_value_pre = 0
            # Emit shipment blocked node
            nodes.append(
                CausalNode(
                    id="shipment",
                    label="Shipment blocked — no route access",
                    kind="trade",
                    before=0,
                    after=0,
                    delta=0,
                    reason_code=ship_reason,
                    parent_ids=("command", "route_established"),
                )
            )
            nodes.append(
                CausalNode(
                    id="trade_revenue",
                    label="Trade revenue 0 (blocked)",
                    kind="trade",
                    before=0,
                    after=0,
                    delta=0,
                    reason_code=ship_reason,
                    parent_ids=("shipment", "river_price", "route_reliability"),
                )
            )
            nodes.append(
                CausalNode(
                    id="transport_cost",
                    label="Transport cost 0 (blocked)",
                    kind="trade",
                    before=0,
                    after=0,
                    delta=0,
                    reason_code=ship_reason,
                    parent_ids=("shipment", "route_cost_per_unit"),
                )
            )
            nodes.append(
                CausalNode(
                    id="ship_quantity_value",
                    label="Ship quantity value 0 (blocked)",
                    kind="trade",
                    before=0,
                    after=0,
                    delta=0,
                    reason_code=ship_reason,
                    parent_ids=("shipment", "inventory"),
                )
            )
            # Truthful cash/inventory after trade (no movement)
            nodes.append(
                CausalNode(
                    id="cash_after_trade",
                    label="Cash after trade 0 (blocked)",
                    kind="cash",
                    before=cash,
                    after=cash,
                    delta=0,
                    reason_code=ship_reason,
                    parent_ids=("cash_after_command", "trade_revenue", "transport_cost"),
                )
            )
            nodes.append(
                CausalNode(
                    id="inventory_after_trade",
                    label="Inventory after trade 0 (blocked)",
                    kind="inventory",
                    before=inventory_final_pre_ship,
                    after=inventory_final_pre_ship,
                    delta=0,
                    reason_code=ship_reason,
                    parent_ids=("inventory", "shipment"),
                )
            )
            effects.append(
                DomainEffect(
                    metric="shipment",
                    before=0,
                    after=0,
                    delta=0,
                    reason_code=ship_reason,
                )
            )
        else:
            # Established: shared shipment primitive (timing: revenue at resolved River price)
            assert requested is not None
            (
                ship_effective,
                ship_delivered,
                ship_revenue,
                ship_cost,
                trade_cash,
                inventory_final,
                ship_reason,
            ) = resolve_shipment(
                requested=requested,
                route_established=True,
                route_capacity=route_capacity,
                route_reliability_bps=route_reliability_bps,
                transport_cost_per_unit=transport_cost_per_unit,
                inventory_final_pre_ship=inventory_final_pre_ship,
                cash=cash,
                river_price=river_new_price,
            )
            # Update cash — capture before values for truthful trace
            cash_before_trade = cash
            cash_after_ship = cash + trade_cash
            if cash_after_ship < 0:
                cash_after_ship = 0
            cash = cash_after_ship
            # Compute ship_quantity_value at home price (old price)
            value_before_ship = _value(inventory_final_pre_ship, before_price)
            value_after_ship = _value(inventory_final, before_price)
            ship_quantity_value_pre = value_after_ship - value_before_ship
            # Arbitrage margin using resolved prices (for driver decision, not wealth)
            # river_sale_value - transport_cost - resolved_home_opportunity
            arbitrage_margin = ship_revenue - ship_cost - (ship_effective * new_price // 1000)
            # Store for driver reasoning (attach to trace via reason_code later)
            # Keep for later use in story drivers via closure variable
            # Use a local to pass to driver section: we store in a variable that survives
            # We'll stash in a deterministic way: create a node that encodes the margin
            # (no extra node needed, just keep variable arbitrage_margin for driver)
            # Emit nodes with truthful parents
            nodes.append(
                CausalNode(
                    id="shipment",
                    label=f"Shipment {ship_effective}/{requested} (delivered {ship_delivered}, reason {ship_reason})",
                    kind="trade",
                    before=inventory_final_pre_ship,
                    after=inventory_final,
                    delta=-ship_effective,
                    reason_code=ship_reason,
                    parent_ids=(
                        "command",
                        "route_established",
                        "route_capacity",
                        "inventory",
                        "route_cost_per_unit",
                        "cash_after_command",
                    ),
                )
            )
            nodes.append(
                CausalNode(
                    id="trade_revenue",
                    label=f"Trade revenue {ship_delivered}×{river_new_price} → {ship_revenue}",
                    kind="trade",
                    before=0,
                    after=ship_revenue,
                    delta=ship_revenue,
                    reason_code="trade_revenue_at_river_price",
                    parent_ids=("shipment", "river_price", "route_reliability"),
                )
            )
            nodes.append(
                CausalNode(
                    id="transport_cost",
                    label=f"Transport cost {ship_effective}×{transport_cost_per_unit} → {ship_cost}",
                    kind="trade",
                    before=0,
                    after=-ship_cost,
                    delta=-ship_cost,
                    reason_code="transport_cost",
                    parent_ids=("shipment", "route_cost_per_unit"),
                )
            )
            nodes.append(
                CausalNode(
                    id="ship_quantity_value",
                    label=f"Ship quantity value {value_before_ship} → {value_after_ship} (delta {ship_quantity_value_pre:+})",
                    kind="trade",
                    before=value_before_ship,
                    after=value_after_ship,
                    delta=ship_quantity_value_pre,
                    reason_code="ship_quantity_value" if ship_effective > 0 else "no_ship",
                    parent_ids=("shipment", "inventory"),
                )
            )
            # Cash after trade — truthful parentage for cash_effect
            nodes.append(
                CausalNode(
                    id="cash_after_trade",
                    label=f"Cash after trade {cash_before_trade} → {cash_after_ship} (revenue {ship_revenue} cost {ship_cost})",
                    kind="cash",
                    before=cash_before_trade,
                    after=cash_after_ship,
                    delta=trade_cash,
                    reason_code="cash_after_trade",
                    parent_ids=("cash_after_command", "trade_revenue", "transport_cost"),
                )
            )
            # Inventory after trade — truthful parent for price revaluation
            nodes.append(
                CausalNode(
                    id="inventory_after_trade",
                    label=f"Inventory after trade {inventory_final_pre_ship} → {inventory_final}",
                    kind="inventory",
                    before=inventory_final_pre_ship,
                    after=inventory_final,
                    delta=-ship_effective,
                    reason_code=ship_reason,
                    parent_ids=("inventory", "shipment"),
                )
            )
            effects.append(
                DomainEffect(
                    metric="shipment",
                    before=inventory_final_pre_ship,
                    after=inventory_final,
                    delta=-ship_effective,
                    reason_code=ship_reason,
                )
            )
            effects.append(
                DomainEffect(
                    metric="trade_revenue",
                    before=0,
                    after=ship_revenue,
                    delta=ship_revenue,
                    reason_code="trade_revenue",
                )
            )
            effects.append(
                DomainEffect(
                    metric="transport_cost",
                    before=0,
                    after=-ship_cost,
                    delta=-ship_cost,
                    reason_code="transport_cost",
                )
            )
            effects.append(
                DomainEffect(
                    metric="ship_quantity_value",
                    before=value_before_ship,
                    after=value_after_ship,
                    delta=ship_quantity_value_pre,
                    reason_code="ship_quantity_value",
                )
            )
            # Update inventory overall delta after ship
            overall_inventory_delta = inventory_final - before_inventory
            # Add/override inventory effect to reflect final after ship
            # We already have inventory_harvest/inventory effect for pre-ship; add final inventory effect
            effects.append(
                DomainEffect(
                    metric="inventory_after_ship",
                    before=inventory_final_pre_ship,
                    after=inventory_final,
                    delta=-ship_effective,
                    reason_code=ship_reason,
                )
            )
        # For ship case, overall_inventory_delta is final after ship
        overall_inventory_delta = inventory_final - before_inventory
    else:
        # Not a ship command — emit zero shipment nodes for trace completeness
        ship_effective = 0
        ship_delivered = 0
        ship_revenue = 0
        ship_cost = 0
        ship_reason = "no_shipment"
        trade_cash = 0
        arbitrage_margin = 0
        ship_quantity_value_pre = 0
        nodes.append(
            CausalNode(
                id="shipment",
                label="No shipment",
                kind="trade",
                before=0,
                after=0,
                delta=0,
                reason_code=ship_reason,
                parent_ids=("command",),
            )
        )
        nodes.append(
            CausalNode(
                id="trade_revenue",
                label="Trade revenue 0",
                kind="trade",
                before=0,
                after=0,
                delta=0,
                reason_code=ship_reason,
                parent_ids=("shipment", "river_price", "route_reliability"),
            )
        )
        nodes.append(
            CausalNode(
                id="transport_cost",
                label="Transport cost 0",
                kind="trade",
                before=0,
                after=0,
                delta=0,
                reason_code=ship_reason,
                parent_ids=("shipment", "route_cost_per_unit"),
            )
        )
        nodes.append(
            CausalNode(
                id="ship_quantity_value",
                label="Ship quantity value 0",
                kind="trade",
                before=0,
                after=0,
                delta=0,
                reason_code=ship_reason,
                parent_ids=("shipment", "inventory"),
            )
        )
        nodes.append(
            CausalNode(
                id="cash_after_trade",
                label="Cash after trade 0 (no shipment)",
                kind="cash",
                before=cash,
                after=cash,
                delta=0,
                reason_code=ship_reason,
                parent_ids=("cash_after_command", "trade_revenue", "transport_cost"),
            )
        )
        nodes.append(
            CausalNode(
                id="inventory_after_trade",
                label="Inventory after trade 0 (no shipment)",
                kind="inventory",
                before=inventory_final_pre_ship,
                after=inventory_final,
                delta=0,
                reason_code=ship_reason,
                parent_ids=("inventory", "shipment"),
            )
        )
        effects.append(
            DomainEffect(
                metric="shipment",
                before=0,
                after=0,
                delta=0,
                reason_code=ship_reason,
            )
        )
        overall_inventory_delta = inventory_final - before_inventory

    # 6. Valuation — exact decomposition of wealth (now with ship + Section 13 finished goods)
    # wealth_before = cash_before + value_grain_before + value_finished_before
    # where finished valued at FINISHED_GOODS_PRICE (urban buyer, stable)
    # Section 13 adds craft/sell_finished/hire that change finished_inventory / labour
    from app.engine.actor import FINISHED_GOODS_PRICE, FINISHED_GOODS_PRICE_RIVER_EXTRA

    finished_price = FINISHED_GOODS_PRICE + (
        FINISHED_GOODS_PRICE_RIVER_EXTRA if "river_contracts" in state.legacies else 0
    )
    # grain valuation at home price
    value_before = _value(before_inventory, before_price)
    value_after_buy = _value(inventory_before_settlement, before_price)
    value_after_harvest = _value(inventory_final_pre_ship, before_price)
    value_after_ship = _value(inventory_final, before_price)
    value_after = _value(inventory_final, new_price)
    # finished goods valuation at finished_price (stable)
    finished_before_val = _value(before_finished, finished_price)
    finished_after_val = _value(finished_inventory, finished_price)
    finished_quantity_value = finished_after_val - finished_before_val
    finished_price_effect = 0  # price stable, no revaluation for finished
    wealth_before = before_cash + value_before + finished_before_val
    wealth_after = cash + value_after + finished_after_val
    purchase_quantity_value = value_after_buy - value_before
    harvest_quantity_value = value_after_harvest - value_after_buy
    ship_quantity_value = value_after_ship - value_after_harvest
    # For ship commands, ship_quantity_value should match earlier computed pre value; assert consistency
    # But for non-ship, it's 0
    assert ship_quantity_value == ship_quantity_value_pre, (
        f"ship mismatch {ship_quantity_value} vs {ship_quantity_value_pre}"
    )
    quantity_value_effect = (
        purchase_quantity_value
        + harvest_quantity_value
        + ship_quantity_value
        + finished_quantity_value
    )
    price_value_effect = value_after - value_after_ship + finished_price_effect
    cash_effect = cash - before_cash
    wealth_delta = cash_effect + quantity_value_effect + price_value_effect
    # Sanity: wealth_after - wealth_before must equal wealth_delta
    assert wealth_after - wealth_before == wealth_delta, (
        f"wealth delta mismatch {wealth_after - wealth_before} vs {wealth_delta} (wealth {wealth_before}->{wealth_after})"
    )
    # For backward compat when ship==0 and no finished, quantity_value_effect == purchase+harvest
    if ship_quantity_value == 0 and finished_quantity_value == 0:
        assert quantity_value_effect == purchase_quantity_value + harvest_quantity_value

    # Purchase/sell quantity — value of bought/sold grain at old price
    if command.type == "buy_grain":
        purchase_parents: tuple[str, ...] = ("command", "inventory_after_command")
        purchase_reason = "purchase_quantity_value"
        purchase_label = f"Purchase quantity value {value_before} → {value_after_buy} (delta {purchase_quantity_value:+})"
    elif command.type == "sell_grain":
        purchase_parents = ("command", "inventory_after_command")
        purchase_reason = "sell_quantity_value"
        purchase_label = f"Sell quantity value {value_before} → {value_after_buy} (delta {purchase_quantity_value:+})"
    else:
        purchase_parents = ("command",)
        purchase_reason = "no_purchase"
        purchase_label = f"Purchase quantity value {value_before} → {value_after_buy} (delta {purchase_quantity_value:+})"
    nodes.append(
        CausalNode(
            id="purchase_quantity_value",
            label=purchase_label,
            kind="purchase_quantity_value",
            before=value_before,
            after=value_after_buy,
            delta=purchase_quantity_value,
            reason_code=purchase_reason,
            parent_ids=purchase_parents,
        )
    )
    # Harvest quantity — value of harvested grain at old price (storage-constrained)
    if settle_reason == "capped_by_storage":
        harvest_reason = "harvest_quantity_capped_by_storage"
        harvest_label = f"Harvest quantity value {value_after_buy} → {value_after_harvest} (delta {harvest_quantity_value:+}, capped)"
    else:
        if world == "drought":
            harvest_reason = "drought_harvest_quantity_value"
            harvest_label = f"Harvest quantity value {value_after_buy} → {value_after_harvest} (delta {harvest_quantity_value:+})"
        else:
            harvest_reason = "harvest_quantity_value"
            harvest_label = f"Harvest quantity value {value_after_buy} → {value_after_harvest} (delta {harvest_quantity_value:+})"
    nodes.append(
        CausalNode(
            id="harvest_quantity_value",
            label=harvest_label,
            kind="harvest_quantity_value",
            before=value_after_buy,
            after=value_after_harvest,
            delta=harvest_quantity_value,
            reason_code=harvest_reason,
            parent_ids=("farm_output", "storage_capacity", "inventory"),
        )
    )
    # Ship quantity value node already emitted as trade node above
    # Section 13 — finished goods valuation nodes
    if finished_quantity_value != 0 or before_finished != 0 or finished_inventory != 0:
        # Emit finished quantity value node if there is movement or holding
        # Use finished_inventory change at finished_price
        # Determine parents: craft or sell_finished
        if command.type in ("craft_goods", "sell_finished_goods"):
            finished_parents: tuple[str, ...] = (
                ("finished_inventory", "craft_conversion")
                if command.type == "craft_goods"
                else ("finished_inventory", "finished_price")
            )
            finished_reason = "finished_quantity_value"
        else:
            finished_parents = ("finished_inventory",)
            finished_reason = (
                "finished_quantity_value_noop"
                if finished_quantity_value == 0
                else "finished_quantity_value"
            )
        nodes.append(
            CausalNode(
                id="finished_quantity_value",
                label=f"Finished quantity value {finished_before_val} → {finished_after_val} (delta {finished_quantity_value:+})",
                kind="finished_inventory",
                before=finished_before_val,
                after=finished_after_val,
                delta=finished_quantity_value,
                reason_code=finished_reason,
                parent_ids=finished_parents,
            )
        )
        # Also emit finished price node if not already (for non-sell_finished cases)
        if not any(n.id == "finished_price" for n in nodes):
            nodes.append(
                CausalNode(
                    id="finished_price",
                    label=f"Finished price {finished_price}",
                    kind="finished_price",
                    before=finished_price,
                    after=finished_price,
                    delta=0,
                    reason_code="finished_price_stable",
                    parent_ids=(),
                )
            )
    # Combined quantity value — sum of purchase, harvest, ship, finished
    if ship_quantity_value != 0 and finished_quantity_value != 0:
        quantity_parents = (
            "purchase_quantity_value",
            "harvest_quantity_value",
            "ship_quantity_value",
            "finished_quantity_value",
        )
    elif ship_quantity_value != 0:
        quantity_parents = (
            "purchase_quantity_value",
            "harvest_quantity_value",
            "ship_quantity_value",
        )
    elif finished_quantity_value != 0:
        quantity_parents = (
            "purchase_quantity_value",
            "harvest_quantity_value",
            "finished_quantity_value",
        )
    else:
        quantity_parents = ("purchase_quantity_value", "harvest_quantity_value")
    nodes.append(
        CausalNode(
            id="quantity_value_effect",
            label=f"Quantity value {value_before + finished_before_val} → {value_after_ship + finished_after_val} (delta {quantity_value_effect:+})",
            kind="quantity_value_effect",
            before=value_before + finished_before_val,
            after=value_after_ship + finished_after_val,
            delta=quantity_value_effect,
            reason_code="quantity_value_effect",
            parent_ids=quantity_parents,
        )
    )
    nodes.append(
        CausalNode(
            id="price_value_effect",
            label=f"Price revaluation {value_after_ship} → {value_after} "
            f"(delta {price_value_effect:+})",
            kind="price_value_effect",
            before=value_after_ship,
            after=value_after,
            delta=price_value_effect,
            reason_code="price_revalued_stored_grain",
            parent_ids=("inventory_after_trade", "price"),
        )
    )
    nodes.append(
        CausalNode(
            id="cash_effect",
            label=f"Cash effect {before_cash} → {cash} (delta {cash_effect:+})",
            kind="cash",
            before=before_cash,
            after=cash,
            delta=cash_effect,
            reason_code=cmd_reason,
            parent_ids=("cash_after_trade",),
        )
    )
    nodes.append(
        CausalNode(
            id="wealth",
            label=f"Wealth {wealth_before} → {wealth_after} (delta {wealth_delta:+})",
            kind="wealth",
            before=wealth_before,
            after=wealth_after,
            delta=wealth_delta,
            reason_code="wealth_from_cash_and_valuation",
            parent_ids=("cash_effect", "quantity_value_effect", "price_value_effect"),
        )
    )
    effects.append(
        DomainEffect(
            metric="purchase_quantity_value",
            before=value_before,
            after=value_after_buy,
            delta=purchase_quantity_value,
            reason_code="purchase_quantity_value",
        )
    )
    effects.append(
        DomainEffect(
            metric="harvest_quantity_value",
            before=value_after_buy,
            after=value_after_harvest,
            delta=harvest_quantity_value,
            reason_code="harvest_quantity_value",
        )
    )
    # Ship quantity value domain effect already added in route settlement for ship case; for non-ship add here
    if not is_ship_command or ship_effective == 0:
        effects.append(
            DomainEffect(
                metric="ship_quantity_value",
                before=value_after_harvest,
                after=value_after_ship,
                delta=ship_quantity_value,
                reason_code="ship_quantity_value",
            )
        )
    effects.append(
        DomainEffect(
            metric="quantity_value_effect",
            before=value_before + finished_before_val,
            after=value_after_ship + finished_after_val,
            delta=quantity_value_effect,
            reason_code="quantity_value_effect",
        )
    )
    effects.append(
        DomainEffect(
            metric="price_value_effect",
            before=value_after_ship + finished_after_val,
            after=value_after + finished_after_val,
            delta=price_value_effect,
            reason_code="price_value_effect",
        )
    )
    effects.append(
        DomainEffect(
            metric="cash_effect",
            before=before_cash,
            after=cash,
            delta=cash_effect,
            reason_code=cmd_reason,
        )
    )
    effects.append(
        DomainEffect(
            metric="wealth",
            before=wealth_before,
            after=wealth_after,
            delta=wealth_delta,
            reason_code="wealth_change",
        )
    )

    # Next player state — include finished goods and skilled labour (Section 13)
    next_player = PlayerState(
        cash=cash,
        inventory=InventoryState(grain=inventory_final, finished_goods=finished_inventory),
        farm_capacity=farm_capacity,
        storage_capacity=storage_capacity,
        skilled_labour=skilled_labour,
    )
    # Demand for next state's market persists effective demand if epilogue (so next turn's before_demand reflects shift)
    try:
        next_market_demand = _eff_demand  # type: ignore[name-defined]
    except NameError:
        next_market_demand = before_demand
    next_market = MarketState(
        supply=next_supply,
        demand=next_market_demand,
        base_price=base_price,
        current_price=new_price,
        responsiveness=responsiveness,
        max_movement_bps=max_movement_bps,
        regional_output=regional_base,
    )
    next_river_market = MarketState(
        supply=river_supply_next,
        demand=before_river_demand,
        base_price=river_base_price,
        current_price=river_new_price,
        responsiveness=river_responsiveness,
        max_movement_bps=river_max_movement_bps,
    )
    # Next route state
    from app.domain.types import RouteState as RouteStateType

    next_route = RouteStateType(
        transport_cost_per_unit=transport_cost_per_unit,
        capacity=route_capacity,
        reliability_bps=route_reliability_bps,
        established=route_established,
        delay_turns=before_route.delay_turns,
        event_exposure=before_route.event_exposure,
    )
    next_state = GameState(
        turn=state.turn + 1,
        run_seed=state.run_seed,
        ruleset_version=state.ruleset_version,
        player=next_player,
        market=next_market,
        river_market=next_river_market,
        route=next_route,
        legacies=state.legacies,
    )

    # Build story drivers — exact partitions of wealth_delta, filtered, ranked by wealth-bps
    wealth_before_for_bps = wealth_before if wealth_before > 0 else 1

    def _bps(impact: int) -> int:
        return abs(impact) * 10_000 // wealth_before_for_bps

    candidates: list[OutcomeDriver] = []

    # Trade cash split for driver accounting
    if is_ship_command and ship_effective > 0:
        trade_cash = ship_revenue - ship_cost
        command_cash = cash_effect - trade_cash
    else:
        trade_cash = 0
        command_cash = cash_effect

    # Candidate 1: command cost (cash_effect without trade) — only if non-zero
    if command_cash != 0:
        if command.type == "expand_farm":
            label = f"Expanding farm cost {abs(command_cash)}"
            reason = "expand_farm_cost"
        elif command.type == "build_granary":
            label = f"Building granary cost {abs(command_cash)}"
            reason = "build_granary_cost"
        elif command.type == "buy_grain":
            if cmd_reason == "insufficient_cash":
                label = f"Buy grain limited by cash (spent {abs(command_cash)})"
                reason = "buy_limited_cash"
            elif cmd_reason == "insufficient_storage":
                label = f"Buy grain limited by storage (spent {abs(command_cash)})"
                reason = "buy_limited_storage"
            else:
                label = f"Bought grain for {abs(command_cash)}"
                reason = "buy_grain_cost"
        elif command.type == "sell_grain":
            if cmd_reason == "insufficient_inventory":
                label = f"Sell grain limited by inventory (gained {abs(command_cash)})"
                reason = "sell_limited_inventory"
            else:
                label = f"Sold grain for {abs(command_cash)}"
                reason = "sell_grain_revenue"
        elif command.type == "secure_route":
            if cmd_reason == "already_established":
                label = "Route already secured (no cost)"
                reason = "already_established"
            elif cmd_reason == "insufficient_cash_for_route":
                label = "Could not afford to secure route"
                reason = "insufficient_cash_for_route"
            else:
                label = f"Secured river route for {abs(command_cash)}"
                reason = "secure_route_cost"
        else:
            label = f"Cash change {command_cash:+}"
            reason = cmd_reason
        candidates.append(
            OutcomeDriver(
                id="command_cost",
                label=label,
                kind="cash",
                impact_money=command_cash,
                impact_bps=_bps(command_cash),
                reason_code=reason,
                causal_node_ids=("command", "cash_after_command", "cash_effect"),
            )
        )

    # Candidate ship trade — net wealth impact + arbitrage margin at resolved prices
    if is_ship_command and ship_effective > 0:
        net_trade = ship_quantity_value + trade_cash
        # arbitrage_margin uses resolved home price for opportunity cost
        # wealth keeps ship_quantity_value at before_price, but decision uses arbitrage_margin
        # arbitrage_margin already computed; fallback to net_trade calc if not set (should be set)
        try:
            margin = arbitrage_margin
        except NameError:
            margin = ship_revenue - ship_cost - (ship_effective * new_price // 1000)
        # Only add if wealth net !=0 (keeps wealth-bps ranking intact); decision based on margin
        if net_trade != 0:
            if margin > 0:
                label = f"Shipped {ship_effective} grain to River Town for profit {net_trade:+} (revenue {ship_revenue} - cost {ship_cost} + quantity {ship_quantity_value:+}, arbitrage {margin:+} at resolved prices)"
                reason = "profitable_arbitrage"
            elif margin < 0:
                label = f"Shipped {ship_effective} grain to River Town (net {net_trade:+}, revenue {ship_revenue} - cost {ship_cost} + quantity {ship_quantity_value:+}, arbitrage {margin:+} at resolved prices)"
                reason = "unprofitable_shipment"
            else:
                label = f"Shipped {ship_effective} grain to River Town break-even (revenue {ship_revenue} = cost + resolved home value)"
                reason = "break_even_trade"
            # causal path includes river price divergence and home price opportunity
            causal_ids = (
                "command",
                "shipment",
                "river_price",
                "ship_quantity_value",
                "trade_revenue",
                "transport_cost",
                "inventory_after_trade",
                "price",
            )
            candidates.append(
                OutcomeDriver(
                    id="trade_arbitrage",
                    label=label,
                    kind="trade",
                    impact_money=net_trade,
                    impact_bps=_bps(net_trade),
                    reason_code=reason,
                    causal_node_ids=causal_ids,
                )
            )
        elif ship_effective > 0 and net_trade == 0:
            label = f"Shipped {ship_effective} grain to River Town break-even (revenue {ship_revenue} = cost + quantity loss)"
            reason = "break_even_trade"
            causal_ids = ("command", "shipment", "river_price", "ship_quantity_value")
            candidates.append(
                OutcomeDriver(
                    id="trade_arbitrage",
                    label=label,
                    kind="trade",
                    impact_money=0,
                    impact_bps=0,
                    reason_code=reason,
                    causal_node_ids=causal_ids,
                )
            )
            candidates.pop()  # filtered zero

    # Candidate 2: purchase/sell quantity value — only if actually added value
    if purchase_quantity_value != 0:
        # This is the value of bought/sold grain at old price; harvest is separate
        if command.type == "buy_grain":
            # Use actual purchase amount for label if available
            # inventory_after_command - before_inventory is purchase qty
            purchase_qty = inventory_before_settlement - before_inventory
            if cmd_reason in ("insufficient_cash", "insufficient_storage"):
                label = f"Bought {purchase_qty} grain (value {purchase_quantity_value:+}, limited by {cmd_reason})"
                reason = "purchase_quantity_limited"
            else:
                label = f"Bought {purchase_qty} grain (value {purchase_quantity_value:+})"
                reason = "purchase_quantity_value"
            causal_ids = ("command", "inventory_after_command", "purchase_quantity_value")
        elif command.type == "sell_grain":
            sold_qty = before_inventory - inventory_before_settlement
            if cmd_reason == "insufficient_inventory":
                label = f"Sold {sold_qty} grain (value {purchase_quantity_value:+}, limited by inventory)"
                reason = "sell_quantity_limited"
            else:
                label = f"Sold {sold_qty} grain (value {purchase_quantity_value:+})"
                reason = "sell_quantity_value"
            causal_ids = ("command", "inventory_after_command", "purchase_quantity_value")
        else:
            label = f"Purchase quantity value {purchase_quantity_value:+}"
            reason = "purchase_quantity_value"
            causal_ids = ("command", "purchase_quantity_value")
        candidates.append(
            OutcomeDriver(
                id="purchase_quantity",
                label=label,
                kind="valuation",
                impact_money=purchase_quantity_value,
                impact_bps=_bps(purchase_quantity_value),
                reason_code=reason,
                causal_node_ids=causal_ids,
            )
        )

    # Candidate 3: harvest quantity value — only if harvest added (or was capped) value
    if harvest_quantity_value != 0:
        if settle_reason == "capped_by_storage":
            label = f"Storage cap limited harvest (quantity value {harvest_quantity_value:+})"
            reason = "harvest_quantity_capped"
            causal_ids = ("farm_output", "storage_capacity", "inventory", "harvest_quantity_value")
        else:
            if world == "drought":
                label = f"Drought reduced harvest, quantity value {harvest_quantity_value:+}"
                reason = "drought_harvest_quantity_value"
                causal_ids = ("world", "farm_output", "harvest_quantity_value")
            else:
                label = f"Harvest added grain, quantity value {harvest_quantity_value:+}"
                reason = "harvest_quantity_value"
                causal_ids = ("farm_output", "harvest_quantity_value")
        candidates.append(
            OutcomeDriver(
                id="harvest_quantity",
                label=label,
                kind="valuation",
                impact_money=harvest_quantity_value,
                impact_bps=_bps(harvest_quantity_value),
                reason_code=reason,
                causal_node_ids=causal_ids,
            )
        )

    # Candidate 4: price revaluation (home supply -> home price -> valuation)
    if price_value_effect != 0:
        direction = "higher" if price_value_effect > 0 else "lower"
        label = (
            f"{direction.capitalize()} grain price revalued stored grain ({price_value_effect:+})"
        )
        reason = "price_revaluation"
        causal_ids = (
            "farm_output",
            "supply",
            "price_pressure",
            "target_price",
            "price",
            "price_value_effect",
        )
        # For holds where price moves without farm_output
        # change, still include farm_output for chain
        candidates.append(
            OutcomeDriver(
                id="price_revaluation",
                label=label,
                kind="price",
                impact_money=price_value_effect,
                impact_bps=_bps(price_value_effect),
                reason_code=reason,
                causal_node_ids=causal_ids,
            )
        )

    # Filter zero-impact candidates and rank
    candidates = [c for c in candidates if c.impact_money != 0]
    # Rank by impact_bps DESC, id ASC for determinism, keep top 3
    candidates_sorted = sorted(candidates, key=lambda d: (-d.impact_bps, d.id))
    drivers = tuple(candidates_sorted[:3])

    player_outcome = PlayerOutcome(
        wealth_delta=wealth_delta,
        inventory_delta=overall_inventory_delta,
        price_delta=price_delta,
        drivers=drivers,
    )

    trace = CausalTrace(nodes=tuple(nodes))

    return TurnResolution(
        next_state=next_state,
        domain_effects=tuple(effects),
        causal_trace=trace,
        player_outcome=player_outcome,
    )
