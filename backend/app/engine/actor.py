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


def cost_for_quantity(quantity: int, price_milli: int) -> int:
    """Cost in Money for quantity at price_milli (milliunits per unit).

    Floor division — deterministic and conservative.
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

    # Reason determination — exact copy of turn.py priority
    if actual < requested and actual == affordable and actual < available_space:
        reason = "insufficient_cash"
    elif actual < requested and actual == available_space:
        if available_space < affordable:
            reason = "insufficient_storage"
        else:
            reason = "insufficient_cash" if affordable < requested else "insufficient_storage"
        if requested > available_space:
            if affordable < available_space:
                reason = "insufficient_cash"
            else:
                reason = "insufficient_storage"
    elif actual == requested and requested > 0:
        reason = "buy_grain"
    elif actual == 0 and requested > 0:
        if affordable == 0 and available_space > 0:
            reason = "insufficient_cash"
        elif available_space == 0:
            reason = "insufficient_storage"
        else:
            reason = "buy_grain_zero"
    else:
        reason = "buy_grain" if actual > 0 else "buy_grain_zero"

    cash_after = cash - cost
    inventory_after = inventory + actual
    return cash_after, inventory_after, actual, cost, reason


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
