"""Shared actor-level economic primitives — Section 7 extraction.

Single source of truth for harvest / buy / storage / shipment math.
Both `turn.py` (player) and `rivals.py` (Mira/Daran) call these helpers
so rule changes (clamping, costs, yield) cannot diverge.

All helpers are pure, integer, deterministic, and have no FastAPI/DB deps.
Market resolution (_target_price/_bounded_price) and causal-trace construction
remain in `turn.py` — this module is only the actor-level settlement.
"""

from __future__ import annotations

# Constants — single source, re-exported by turn.py for backward compat
YIELD_PER_CAPACITY: int = 10  # grain per farm_capacity under normal
DROUGHT_YIELD_REDUCTION_BPS: int = 4000  # 40% reduction
EXPAND_FARM_COST: int = 500
EXPAND_FARM_DELTA: int = 10
BUILD_GRANARY_COST: int = 300
BUILD_GRANARY_DELTA: int = 50
ROUTE_ESTABLISH_COST: int = 400

# Section 13 — city craft epilogue
GRAIN_PER_LABOUR: int = 10  # grain convertible per labour per turn
FINISHED_PER_GRAIN_NUM: int = 3
FINISHED_PER_GRAIN_DENOM: int = 10  # 10 grain -> 3 finished (30% yield)
FINISHED_GOODS_PRICE: int = 22000  # milliunits per finished unit — regime change: 22 vs raw 0.8 (27×) makes raw collapse matter
FINISHED_GOODS_PRICE_RIVER_EXTRA: int = 0  # river advantage is labour, not price — keep uniform
HIRE_LABOUR_COST: int = 400
HIRE_LABOUR_COST_REPUTATION: int = 200  # Crisis Reputation discount
LAND_NETWORK_EXTRA_GRAIN_PER_TURN: int = 15  # deliberately weak vs labour*10 cap
# Epilogue demand collapse — regime change, not a dip: 410 -> ~100 -> 50 -> 20
# Raw share target storage ≤50% (from 82%) requires raw price ~800-1000, not ~4000
EPILOGUE_RAW_DEMAND: tuple[int, ...] = (80, 30, 10)  # turns 5,6,7 vs agriculture 410
# Crisis Reputation inventory threshold — tuned from measured distribution (~25-40% band)
CRISIS_INVENTORY_THRESHOLD: int = 80  # grain held into drought turn (turn 3)
# Epilogue raw price collapse factor — direct regime shift, not just supply/demand dip
EPILOGUE_RAW_PRICE_COLLAPSE_BPS: int = 2500  # 25% of computed price → ~1000-1200 milli (from ~4000)
EPILOGUE_RAW_PRICE_FLOOR: int = 800  # floor to keep price >0 and trace meaningful


def cost_for_quantity(quantity: int, price_milli: int) -> int:
    """Cost in Money for quantity at price_milli (milliunits per unit).

    Floor division — deterministic and conservative.
    Exact inverse of affordable_quantity: qty*price//1000 <= cash iff qty <= ((cash+1)*1000-1)//price.
    Returns 0 if price_milli is 0 (free) or quantity 0.
    """
    if quantity <= 0 or price_milli <= 0:
        return 0
    return (quantity * price_milli) // 1000


def affordable_quantity(cash: int, price_milli: int, requested: int) -> int:
    """Max quantity affordable at price_milli with cash, floored cost."""
    if requested <= 0:
        return 0
    if price_milli <= 0:
        return requested
    max_affordable = ((cash + 1) * 1000 - 1) // price_milli
    return max_affordable


def value_for(qty: int, price_milli: int) -> int:
    """Inventory value in Money at price_milli."""
    if qty <= 0 or price_milli <= 0:
        return 0
    return (qty * price_milli) // 1000


def compute_farm_output(farm_capacity: int, world: str) -> tuple[int, int, str]:
    """Compute farm output for given capacity and world.

    Returns (farm_output, base_output, reason_code).
    Preserves turn.py's 40% drought reduction exactly.
    """
    base_output = farm_capacity * YIELD_PER_CAPACITY
    if world == "drought":
        farm_output = base_output * (10_000 - DROUGHT_YIELD_REDUCTION_BPS) // 10_000
        reason = "drought_reduced_yield"
    else:
        farm_output = base_output
        reason = "normal_yield"
    return farm_output, base_output, reason


def resolve_buy(
    *,
    cash: int,
    price_milli: int,
    storage_capacity: int,
    inventory: int,
    requested: int,
) -> tuple[int, int, int, int, str]:
    """Resolve a buy_grain command using shared clamping.

    Args:
        cash: cash before buy
        price_milli: Home price before turn (pre-turn)
        storage_capacity: storage limit
        inventory: grain before buy
        requested: grain units requested

    Returns:
        (cash_after, inventory_after, actual, cost, reason_code)
        Mirrors turn.py's exact clamping and reason priority.
    """
    requested = int(requested)
    available_space = storage_capacity - inventory
    if available_space < 0:
        available_space = 0
    affordable = affordable_quantity(cash, price_milli, requested)
    actual = requested
    if actual > affordable:
        actual = affordable
    if actual > available_space:
        actual = available_space
    cost = cost_for_quantity(actual, price_milli)

    # Reason determination — simplified, dead branches removed (S1)
    if actual < requested and actual == affordable and actual < available_space:
        reason = "insufficient_cash"
    elif actual < requested and actual == available_space:
        if requested > available_space:
            if affordable < available_space:
                reason = "insufficient_cash"
            else:
                reason = "insufficient_storage"
        else:
            # Fallback, should not occur with actual==available_space
            reason = "insufficient_storage"
    elif actual == requested and requested > 0:
        reason = "buy_grain"
    else:
        reason = "buy_grain" if actual > 0 else "buy_grain_zero"

    cash_after = cash - cost
    inventory_after = inventory + actual
    return cash_after, inventory_after, actual, cost, reason


def resolve_sell(
    *,
    cash: int,
    price_milli: int,
    inventory: int,
    requested: int,
) -> tuple[int, int, int, int, str]:
    """Resolve a sell_grain command — inverse of buy, at Home price.

    Args:
        cash: cash before sell
        price_milli: Home price before turn (pre-turn)
        inventory: grain before sell
        requested: grain units requested to sell

    Returns:
        (cash_after, inventory_after, actual, revenue, reason_code)
        Clamped to available inventory; uses same integer/milliunit conventions as buy.
    """
    requested = int(requested)
    if requested <= 0:
        return cash, inventory, 0, 0, "sell_grain_zero"
    actual = requested
    if actual > inventory:
        actual = inventory
    revenue = cost_for_quantity(actual, price_milli)
    # S1: simplified, first branch subsumed by second, else unreachable
    if actual < requested:
        reason = "insufficient_inventory"
    elif actual == requested and requested > 0:
        reason = "sell_grain"
    else:
        reason = "sell_grain_zero" if actual == 0 else "sell_grain"
    cash_after = cash + revenue
    inventory_after = inventory - actual
    if inventory_after < 0:
        inventory_after = 0
    return cash_after, inventory_after, actual, revenue, reason


def resolve_storage_settlement(
    *,
    inventory_before: int,
    farm_output: int,
    storage_capacity: int,
) -> tuple[int, int, str]:
    """Settle harvest into inventory with storage cap.

    Returns (inventory_final_pre_ship, delta, reason).
    Mirrors turn.py's capped_by_storage vs harvest_to_inventory.
    """
    inventory_after_harvest = inventory_before + farm_output
    if inventory_after_harvest > storage_capacity:
        inventory_final_pre_ship = storage_capacity
        delta = inventory_final_pre_ship - inventory_before
        reason = "capped_by_storage"
    else:
        inventory_final_pre_ship = inventory_after_harvest
        delta = farm_output
        reason = "harvest_to_inventory"
    return inventory_final_pre_ship, delta, reason


def resolve_shipment(
    *,
    requested: int,
    route_established: bool,
    route_capacity: int,
    route_reliability_bps: int,
    transport_cost_per_unit: int,
    inventory_final_pre_ship: int,
    cash: int,
    river_price: int,
    home_price_for_arbitrage: int | None = None,
) -> tuple[int, int, int, int, int, int, str]:
    """Resolve ship_grain settlement with shared clamping.

    Uses pre-turn cash/inventory and post-resolution river_price for revenue,
    exactly as turn.py does.

    Returns (effective, delivered, revenue, transport_cost, cash_delta, inventory_final, reason).
    When no route, effective=0 and reason=no_route_access.
    When not a ship command, caller should pass requested=0 and treat as no_shipment.
    """
    if not route_established:
        return 0, 0, 0, 0, 0, inventory_final_pre_ship, "no_route_access"
    # Established path — compute affordable/capacity/inventory clamping
    requested = int(requested)
    if transport_cost_per_unit <= 0:
        affordable = requested
    else:
        affordable = ((cash + 1) * 1000 - 1) // transport_cost_per_unit
        if affordable < 0:
            affordable = 0
    available_by_capacity = route_capacity
    available_by_inventory = inventory_final_pre_ship
    effective = requested
    if effective > affordable:
        effective = affordable
    if effective > available_by_capacity:
        effective = available_by_capacity
    if effective > available_by_inventory:
        effective = available_by_inventory
    if effective < 0:
        effective = 0

    if effective < requested:
        if (
            affordable < requested
            and affordable <= available_by_capacity
            and affordable <= available_by_inventory
        ):
            reason = "insufficient_cash_for_transport"
        elif (
            available_by_capacity < requested
            and available_by_capacity <= available_by_inventory
            and available_by_capacity <= affordable
        ):
            reason = "limited_by_capacity"
        elif available_by_inventory < requested:
            reason = "insufficient_inventory"
        else:
            reason = "ship_limited"
    else:
        reason = "ship_grain"

    delivered = effective * route_reliability_bps // 10_000
    revenue = (delivered * river_price) // 1000
    transport_cost = (effective * transport_cost_per_unit) // 1000
    cash_delta = revenue - transport_cost
    inventory_final = inventory_final_pre_ship - effective
    if inventory_final < 0:
        inventory_final = 0
    return effective, delivered, revenue, transport_cost, cash_delta, inventory_final, reason


def resolve_expand_farm(
    *,
    cash: int,
    farm_capacity: int,
) -> tuple[int, int, int, str]:
    """Shared expand_farm affordability/mutation.

    Returns (cash_after, farm_after, farm_delta, reason_code).
    """
    if cash >= EXPAND_FARM_COST:
        return (
            cash - EXPAND_FARM_COST,
            farm_capacity + EXPAND_FARM_DELTA,
            EXPAND_FARM_DELTA,
            "expand_farm",
        )
    return cash, farm_capacity, 0, "insufficient_cash_for_expand"


def resolve_build_granary(
    *,
    cash: int,
    storage_capacity: int,
) -> tuple[int, int, int, str]:
    """Shared build_granary affordability/mutation.

    Returns (cash_after, storage_after, storage_delta, reason_code).
    """
    if cash >= BUILD_GRANARY_COST:
        return (
            cash - BUILD_GRANARY_COST,
            storage_capacity + BUILD_GRANARY_DELTA,
            BUILD_GRANARY_DELTA,
            "build_granary",
        )
    return cash, storage_capacity, 0, "insufficient_cash_for_granary"


def resolve_secure_route(
    *,
    cash: int,
    route_established: bool,
) -> tuple[int, bool, int, str]:
    """Shared secure_route affordability/mutation.

    Returns (cash_after, route_after, delta, reason_code).
    Delta is 1 if newly established else 0.
    Reasons: secure_route, already_established, insufficient_cash_for_route.
    """
    if route_established:
        return cash, True, 0, "already_established"
    if cash >= ROUTE_ESTABLISH_COST:
        return cash - ROUTE_ESTABLISH_COST, True, 1, "secure_route"
    return cash, False, 0, "insufficient_cash_for_route"


def ship_margin(
    river_price: int,
    transport_cost_per_unit: int,
    home_price: int,
    reliability_bps: int = 10000,
) -> int:
    """Pure ship margin at resolved prices: river*reliability - transport - home.

    Single source for engine/harness/mapper. All callers must use this instead
    of inlining `river_price - transport - home_price`.
    Returns milliunits margin (same units as prices); positive means profitable
    after reliability. Defaults to 10000 (fully reliable) for backward compat.
    """
    return (river_price * reliability_bps // 10_000) - transport_cost_per_unit - home_price


def resolve_craft(
    *,
    grain_inventory: int,
    skilled_labour: int,
    requested: int,
    efficiency_num: int = FINISHED_PER_GRAIN_NUM,
    efficiency_den: int = FINISHED_PER_GRAIN_DENOM,
) -> tuple[int, int, int, int, str]:
    """Resolve craft_goods — grain -> finished_goods capped by labour.

    Returns (grain_after, finished_produced, actual_grain_consumed, finished_out, reason).
    finished_out = actual * efficiency_num // efficiency_den.
    Reasons: craft_goods, skilled_labour_limited, insufficient_inventory, craft_zero.
    """
    requested = int(requested)
    if requested <= 0:
        return grain_inventory, 0, 0, 0, "craft_zero"
    max_by_grain = grain_inventory
    max_by_labour = skilled_labour * GRAIN_PER_LABOUR
    # Determine binding limit
    actual = requested
    if actual > max_by_grain:
        actual = max_by_grain
    if actual > max_by_labour:
        actual = max_by_labour
    if actual <= 0:
        if max_by_labour <= 0 and skilled_labour == 0:
            return grain_inventory, 0, 0, 0, "no_skilled_labour"
        if max_by_labour <= 0:
            return grain_inventory, 0, 0, 0, "skilled_labour_limited"
        return grain_inventory, 0, 0, 0, "insufficient_inventory"
    finished = (actual * efficiency_num) // efficiency_den
    grain_after = grain_inventory - actual
    # Reason: if actual limited by labour vs inventory
    if actual == max_by_labour and actual < requested:
        reason = "skilled_labour_limited"
    elif actual == max_by_grain and actual < requested:
        reason = "insufficient_inventory"
    elif actual < requested:
        # Could be both, prefer labour as binding per spec
        if max_by_labour <= max_by_grain:
            reason = "skilled_labour_limited"
        else:
            reason = "insufficient_inventory"
    else:
        reason = "craft_goods"
    return grain_after, finished, actual, finished, reason


def resolve_sell_finished(
    *,
    cash: int,
    finished_inventory: int,
    price_milli: int,
    requested: int,
) -> tuple[int, int, int, int, str]:
    """Resolve sell_finished_goods at urban price.

    Returns (cash_after, finished_after, actual, revenue, reason).
    Clamped to inventory; same integer conventions as sell_grain.
    """
    requested = int(requested)
    if requested <= 0:
        return cash, finished_inventory, 0, 0, "sell_finished_zero"
    actual = requested
    if actual > finished_inventory:
        actual = finished_inventory
    revenue = cost_for_quantity(actual, price_milli)
    if actual < requested:
        reason = "insufficient_finished_inventory"
    elif actual == requested and requested > 0:
        reason = "sell_finished_goods"
    else:
        reason = "sell_finished_zero" if actual == 0 else "sell_finished_goods"
    cash_after = cash + revenue
    finished_after = finished_inventory - actual
    if finished_after < 0:
        finished_after = 0
    return cash_after, finished_after, actual, revenue, reason


def resolve_hire_labour(
    *,
    cash: int,
    skilled_labour: int,
    has_reputation: bool = False,
) -> tuple[int, int, int, str]:
    """Resolve hire_labour — +1 labour, consumes turn, cost depends on reputation.

    Returns (cash_after, labour_after, delta, reason).
    """
    cost = HIRE_LABOUR_COST_REPUTATION if has_reputation else HIRE_LABOUR_COST
    if cash < cost:
        return cash, skilled_labour, 0, "insufficient_cash_for_hire"
    return (
        cash - cost,
        skilled_labour + 1,
        1,
        "hire_labour" if not has_reputation else "hire_labour_cheaper_with_reputation",
    )
