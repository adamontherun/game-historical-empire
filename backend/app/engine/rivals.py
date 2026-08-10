"""Deterministic rival engine — Section 7.

Mira (storage/trade/flexible, moderate risk, reacts early to warning) and
Daran (farmland scale, aggressive, vulnerable) via integer/bps scoring
and shared actor primitives.

All scoring is integer/bps with deterministic tie-break via rng_for only
on exact equal scores. Prose signal strings are never parsed; structured
threat `next_world_known` drives behavior.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.types import InventoryState, PlayerCommand, WorldCondition
from app.engine.actor import (
    BUILD_GRANARY_COST,
    BUILD_GRANARY_DELTA,
    EXPAND_FARM_COST,
    EXPAND_FARM_DELTA,
    ROUTE_ESTABLISH_COST,
    YIELD_PER_CAPACITY,
    compute_farm_output,
    cost_for_quantity,
    resolve_buy,
    resolve_shipment,
    resolve_storage_settlement,
    value_for,
)
from app.engine.rng import rng_for
from app.engine.rounding import mul_basis_points

RivalId = Literal["mira", "daran"]
CommandType = Literal[
    "expand_farm", "build_granary", "buy_grain", "hold", "secure_route", "ship_grain"
]


class RivalProfile(BaseModel):
    """Personality — preferences and risk, not economic state."""

    model_config = ConfigDict(frozen=True)

    id: RivalId = Field(description="Rival identity")
    preferences_bps: dict[str, int] = Field(
        description="Preference per command type in bps (10_000 = 100%)"
    )
    risk_cash_floor: int = Field(description="Cash floor for risk penalty")
    risk_penalty_bps: int = Field(
        description="Risk multiplier when cash would drop below floor (e.g. 8000 = -20%)"
    )
    # Exposure tweak tag for bespoke logic in scoring
    exposure_tag: str = Field(description="farm_penalize or farm_reward")


class RivalState(BaseModel):
    """Economic state — cash/inventory/capacities/route, no headline."""

    model_config = ConfigDict(frozen=True)

    cash: int = Field(ge=0, description="Rival cash")
    inventory: InventoryState = Field(description="Rival grain inventory")
    farm_capacity: int = Field(ge=0, description="Farm capacity")
    storage_capacity: int = Field(ge=0, description="Storage capacity")
    route_established: bool = Field(description="River route established for rival")


class RivalTurnResult(BaseModel):
    """Structured outcome for one rival on one turn."""

    model_config = ConfigDict(frozen=True)

    rival_id: RivalId = Field(description="Which rival")
    before: RivalState = Field(description="State before turn")
    command: PlayerCommand = Field(description="Chosen command")
    after: RivalState = Field(description="State after turn")
    headline: str = Field(description="Truthful headline derived from resolved outcome")
    cash_delta: int = Field(description="after.cash - before.cash")
    inventory_delta: int = Field(description="after.inventory.grain - before.inventory.grain")
    cash_effect: int = Field(description="Same as cash_delta for accounting parity")
    quantity_value_effect: int = Field(
        description="value(after.inv, home_pre) - value(before.inv, home_pre)"
    )
    price_value_effect: int = Field(
        description="value(after.inv, home_resolved) - value(after.inv, home_pre)"
    )
    wealth_delta: int = Field(
        description="cash_effect + quantity + price (mirrors player decomposition)"
    )
    wealth_before: int = Field(description="Wealth before at home_pre")
    wealth_after: int = Field(description="Wealth after at home_resolved")


# Preference tables — 10_000 = 100%, integer bps
# Mira is farm-averse, Daran farm-hungry — integer bps preserves determinism.
MIRA_PREFERENCES: dict[str, int] = {
    "expand_farm": 4500,
    "build_granary": 15000,
    "buy_grain": 13000,
    "hold": 10000,
    "secure_route": 14500,
    "ship_grain": 12000,
}
DARAN_PREFERENCES: dict[str, int] = {
    "expand_farm": 16000,
    "build_granary": 7000,
    "buy_grain": 11000,
    "hold": 10000,
    "secure_route": 6000,
    "ship_grain": 5000,
}

MIRA_PROFILE = RivalProfile(
    id="mira",
    preferences_bps=MIRA_PREFERENCES,
    risk_cash_floor=300,
    risk_penalty_bps=8000,
    exposure_tag="farm_penalize",
)
DARAN_PROFILE = RivalProfile(
    id="daran",
    preferences_bps=DARAN_PREFERENCES,
    risk_cash_floor=200,
    risk_penalty_bps=9500,
    exposure_tag="farm_reward",
)

# Canonical starts — unequal for characterization
MIRA_START_STATE = RivalState(
    cash=1200,
    inventory=InventoryState(grain=25),
    farm_capacity=5,
    storage_capacity=250,
    route_established=False,
)
DARAN_START_STATE = RivalState(
    cash=1400,
    inventory=InventoryState(grain=15),
    farm_capacity=12,
    storage_capacity=150,
    route_established=False,
)

# Headline templates — truthful, derived from resolved outcome
HEADLINES_SUCCESS: dict[str, dict[str, str]] = {
    "mira": {
        "expand_farm": "Mira expanded her farm holdings.",
        "build_granary": "Mira leased additional storage.",
        "buy_grain": "Mira accumulated grain reserves.",
        "hold": "Mira is conserving cash.",
        "secure_route": "Mira secured capacity on the river route.",
        "ship_grain": "Mira shipped grain to River Town.",
    },
    "daran": {
        "expand_farm": "Daran bought another large tract of farmland.",
        "build_granary": "Daran added granary capacity.",
        "buy_grain": "Daran stockpiled grain.",
        "hold": "Daran held his position.",
        "secure_route": "Daran secured river access.",
        "ship_grain": "Daran shipped grain to River Town.",
    },
}
HEADLINES_BLOCKED: dict[str, dict[str, str]] = {
    "mira": {
        "expand_farm": "Mira is short of cash after recent investments.",
        "build_granary": "Mira is short of cash and could not lease storage.",
        "buy_grain": "Mira is short of cash and could not buy grain.",
        "secure_route": "Mira is short of cash and could not secure the river route.",
        "ship_grain": "Mira wanted to ship grain but lacked route access.",
        "hold": "Mira is conserving cash.",
    },
    "daran": {
        "expand_farm": "Daran is short of cash after expanding aggressively.",
        "build_granary": "Daran is short of cash and could not build a granary.",
        "buy_grain": "Daran is short of cash and could not buy grain.",
        "secure_route": "Daran is short of cash and could not secure the route.",
        "ship_grain": "Daran wanted to ship grain but lacked route access.",
        "hold": "Daran held his position.",
    },
}


class ObservableContext(BaseModel):
    """Information visible to rivals when choosing (pre-turn)."""

    model_config = ConfigDict(frozen=True)

    turn: int = Field(ge=0)
    world_now: WorldCondition = Field(description="This turn's world (normal/drought)")
    next_world_known: WorldCondition | None = Field(
        description="Structured threat known at this turn (e.g. drought on T3 warning)"
    )
    home_price_pre: int = Field(gt=0)
    river_price_pre: int = Field(gt=0)
    transport_cost_per_unit: int = Field(ge=0)
    route_capacity: int = Field(ge=0)
    reliability_bps: int = Field(ge=0, le=10000)
    home_supply: int = Field(ge=0)
    home_demand: int = Field(ge=0)
    run_seed: str
    ruleset_version: str


class SettlementContext(BaseModel):
    """Economic settlement context post player market resolution."""

    model_config = ConfigDict(frozen=True)

    world_now: WorldCondition
    home_price_pre: int = Field(gt=0)
    river_price_resolved: int = Field(gt=0)
    home_price_resolved: int = Field(gt=0)
    transport_cost_per_unit: int = Field(ge=0)
    route_capacity: int = Field(ge=0)
    reliability_bps: int = Field(ge=0, le=10000)


def _expected_return(
    profile: RivalProfile,
    rival_state: RivalState,
    cmd_type: str,
    obs: ObservableContext,
) -> int:
    """Rough integer expected return in Money for scoring (not canonical wealth).

    Stays integer, conservative, and deterministic. Uses pre-turn prices and
    threat context. Returns 0 for unprofitable / no-return actions.
    """
    qty_default = 10
    home = obs.home_price_pre
    river = obs.river_price_pre
    transport = obs.transport_cost_per_unit
    inv = rival_state.inventory.grain
    cap = rival_state.farm_capacity
    storage = rival_state.storage_capacity
    cap_route = obs.route_capacity

    if cmd_type == "expand_farm":
        # 2 turns of harvest value minus cost
        est = (YIELD_PER_CAPACITY * EXPAND_FARM_DELTA * home // 1000 * 2) - EXPAND_FARM_COST
        return max(0, est)
    if cmd_type == "build_granary":
        farm_out, _, _ = compute_farm_output(cap, obs.world_now)
        tight = (inv + farm_out * 2) > storage
        if profile.id == "mira":
            base = 340 if tight else 160
        else:
            base = 220 if tight else 30
        if obs.next_world_known == "drought":
            if profile.id == "mira":
                base = base * 14 // 10  # Mira +40% for threat
            else:
                base = base * 11 // 10  # Daran +10%
        return max(0, base)
    if cmd_type == "buy_grain":
        space = max(0, storage - inv)
        q = min(qty_default, space)
        if q <= 0:
            return 0
        cost = cost_for_quantity(q, home)
        # Base arbitrage at current spread
        arbitrage = (river - home - transport) * q // 1000
        if obs.next_world_known == "drought":
            # Future home price rise — drought tightens supply, price up ~1200 milli
            # Use conservative 1200 milli gain for 10 grain = 12; boost for Mira
            if profile.id == "mira":
                # Mira anticipates and values the hedge much higher
                return max(0, 240 - cost // 6)
            else:
                # Daran is less reactive, still some value but less
                return max(0, 130 - cost // 6)
        # Without threat, buy is only modestly useful unless arbitrage
        if arbitrage <= 0:
            return max(0, 25 - cost // 8)
        return max(0, arbitrage - cost // 4)
    if cmd_type == "secure_route":
        if rival_state.route_established:
            return 0
        est_per = (river - home - transport) * cap_route // 1000
        if obs.next_world_known == "drought":
            if profile.id == "mira":
                # Mira values early route highly when threat — must beat granary
                return max(0, 600)
            else:
                return max(0, 120)
        if est_per <= 0:
            est_per = 70 if profile.id == "mira" else 40
        return max(0, est_per * 2 - ROUTE_ESTABLISH_COST + (50 if profile.id == "mira" else 0))
    if cmd_type == "ship_grain":
        if not rival_state.route_established:
            return 0
        q = min(qty_default, cap_route, inv + YIELD_PER_CAPACITY * cap)  # approximate with harvest
        if q <= 0:
            return 0
        # Use pre prices for expectation (choice sees pre)
        delivered = q * obs.reliability_bps // 10_000
        revenue = delivered * river // 1000
        cost = q * transport // 1000
        arbitrage = revenue - cost - (q * home // 1000)
        return max(0, arbitrage)
    if cmd_type == "hold":
        return 5
    return 0


def _capital_bps(rival_state: RivalState, cmd_type: str, obs: ObservableContext) -> int:
    """Capital factor in bps: 0 if unaffordable, 5000 if tight, 10000 if comfortable."""
    cost = 0
    if cmd_type == "expand_farm":
        cost = EXPAND_FARM_COST
    elif cmd_type == "build_granary":
        cost = BUILD_GRANARY_COST
    elif cmd_type == "secure_route":
        cost = ROUTE_ESTABLISH_COST
    elif cmd_type == "buy_grain":
        # 10 grain at pre price
        space = max(0, rival_state.storage_capacity - rival_state.inventory.grain)
        q = min(10, space)
        if q <= 0:
            return 0  # no space -> effectively unaffordable for scoring
        cost = cost_for_quantity(q, obs.home_price_pre)
    elif cmd_type == "ship_grain":
        # ship costs transport; check affordable
        q = min(
            10,
            obs.route_capacity,
            rival_state.inventory.grain + YIELD_PER_CAPACITY * rival_state.farm_capacity,
        )
        if q <= 0:
            return 0 if not rival_state.route_established else 5000
        cost = q * obs.transport_cost_per_unit // 1000
        # Need also route established
        if not rival_state.route_established:
            return 0
    elif cmd_type == "hold":
        return 10000
    if cost == 0:
        return 10000
    cash = rival_state.cash
    if cash < cost:
        return 0
    if cash >= 2 * cost:
        return 10000
    return 5000


def _risk_bps(
    profile: RivalProfile,
    rival_state: RivalState,
    cmd_type: str,
    obs: ObservableContext,
) -> int:
    """Risk factor: penalize if post-command cash would be low."""
    cost = 0
    if cmd_type == "expand_farm":
        cost = EXPAND_FARM_COST
    elif cmd_type == "build_granary":
        cost = BUILD_GRANARY_COST
    elif cmd_type == "secure_route":
        cost = ROUTE_ESTABLISH_COST
    elif cmd_type == "buy_grain":
        space = max(0, rival_state.storage_capacity - rival_state.inventory.grain)
        q = min(10, space)
        cost = cost_for_quantity(q, obs.home_price_pre)
    elif cmd_type == "ship_grain":
        q = min(
            10,
            obs.route_capacity,
            rival_state.inventory.grain + YIELD_PER_CAPACITY * rival_state.farm_capacity,
        )
        cost = q * obs.transport_cost_per_unit // 1000
    elif cmd_type == "hold":
        cost = 0
    post_cash = rival_state.cash - cost
    if post_cash < profile.risk_cash_floor:
        return profile.risk_penalty_bps
    return 10000


def _exposure_bps(
    profile: RivalProfile,
    rival_state: RivalState,
    cmd_type: str,
) -> int:
    """Exposure factor: Mira penalizes farm concentration, Daran rewards it."""
    farm = rival_state.farm_capacity
    storage = rival_state.storage_capacity
    # Heuristic: farm-heavy if farm*10 > storage
    farm_heavy = (farm * 10) > storage
    if profile.exposure_tag == "farm_penalize":
        if farm_heavy and cmd_type == "expand_farm":
            return 8000
        if not farm_heavy and cmd_type == "build_granary":
            return 11000
        return 10000
    else:  # farm_reward
        if farm_heavy and cmd_type == "expand_farm":
            return 11000
        if cmd_type == "build_granary" and not farm_heavy:
            return 9000
        return 10000


def score_rival_command(
    profile: RivalProfile,
    rival_state: RivalState,
    cmd: PlayerCommand,
    obs: ObservableContext,
) -> int:
    """Integer/bps score for a given rival + command + observable context.

    score = expected_return * pref_bps * capital_bps * risk_bps * exposure_bps
    scaled via staged //10000 with rounding via mul_basis_points for stability.
    """
    cmd_type = cmd.type
    exp_return = _expected_return(profile, rival_state, cmd_type, obs)
    # If capital is 0, score 0 regardless of prefs (cannot afford)
    capital = _capital_bps(rival_state, cmd_type, obs)
    if capital == 0:
        return 0
    pref = profile.preferences_bps.get(cmd_type, 10000)
    risk = _risk_bps(profile, rival_state, cmd_type, obs)
    exposure = _exposure_bps(profile, rival_state, cmd_type)

    # Threat-aware preference boost already in expected_return for some types,
    # but also apply a direct preference boost for Mira/Daran on warning:
    # Mira more reactive to next_world_known==drought for storage/route/buy
    # (keep integer).
    if obs.next_world_known == "drought":
        if profile.id == "mira" and cmd_type in ("build_granary", "buy_grain", "secure_route"):
            pref = pref * 13000 // 10000
        elif profile.id == "daran" and cmd_type in ("build_granary", "buy_grain", "secure_route"):
            pref = pref * 11000 // 10000

    # Staged multiplication in bps space
    score = exp_return
    score = mul_basis_points(score, pref)
    score = mul_basis_points(score, capital)
    score = mul_basis_points(score, risk)
    score = mul_basis_points(score, exposure)
    return max(0, score)


def choose_rival_command(
    profile: RivalProfile,
    rival_state: RivalState,
    obs: ObservableContext,
) -> PlayerCommand:
    """Deterministically choose rival command via integer scoring.

    Rankings by (-score, deterministically sorted command type) with exact-tie
    rng_for tie-break only. Returns PlayerCommand with quantity=10 for buy/ship
    when applicable (clamping happens at settlement).
    """
    candidates: list[PlayerCommand] = [
        PlayerCommand(type="expand_farm"),
        PlayerCommand(type="build_granary"),
        PlayerCommand(type="buy_grain", quantity=10),
        PlayerCommand(type="hold"),
        PlayerCommand(type="secure_route"),
        PlayerCommand(type="ship_grain", quantity=10),
    ]
    scored: list[tuple[int, str, PlayerCommand]] = []
    for c in candidates:
        s = score_rival_command(profile, rival_state, c, obs)
        scored.append((s, c.type, c))
    # Sort descending by score, then by type for deterministic order
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score = scored[0][0]
    # Gather ties (exact integer equality)
    tied = [c for s, _, c in scored if s == best_score]
    if len(tied) == 1:
        return tied[0]
    # Exact tie → seeded RNG
    rng = rng_for(obs.run_seed, obs.ruleset_version, obs.turn, "rival", profile.id, 0)
    idx = rng.randint(0, len(tied) - 1)
    # Keep deterministic within ties by sorting tied by type then picking
    tied_sorted = sorted(tied, key=lambda c: c.type)
    return tied_sorted[idx]


def _headline_for(
    profile: RivalProfile,
    command: PlayerCommand,
    before: RivalState,
    after: RivalState,
    success: bool,
) -> str:
    """Derive truthful headline from resolved outcome, not intent."""
    pid = profile.id
    typ = command.type
    # Special case: ship without route is blocked even if we tried to score it 0
    if typ == "ship_grain" and not before.route_established:
        return HEADLINES_BLOCKED[pid]["ship_grain"]
    if not success:
        # Generic blocked phrasing per type
        blocked = HEADLINES_BLOCKED[pid].get(typ)
        if blocked:
            return blocked
        return HEADLINES_BLOCKED[pid].get("hold", "Rival could not act.")
    # Success path
    success_map = HEADLINES_SUCCESS[pid]
    return success_map.get(typ, f"{pid.title()} acted.")


def apply_rival_command(
    profile: RivalProfile,
    before: RivalState,
    command: PlayerCommand,
    settlement: SettlementContext,
) -> RivalTurnResult:
    """Execute one rival's full turn via shared primitives with correct timing.

    Buy price = home_price_pre (pre-turn), drought = world_now,
    shipment revenue at river_price_resolved, valuation at home_price_resolved.

    Returns structured RivalTurnResult with full accounting and truthful headline.
    """
    cash = before.cash
    farm = before.farm_capacity
    storage = before.storage_capacity
    inv = before.inventory.grain
    route_established = before.route_established

    world_now = settlement.world_now
    home_pre = settlement.home_price_pre
    river_resolved = settlement.river_price_resolved
    home_resolved = settlement.home_price_resolved

    cmd_type = command.type
    requested_qty = command.quantity if command.quantity is not None else 10
    requested_qty = int(requested_qty) if requested_qty is not None else 10

    # Track success flag and intermediate values
    success = True
    cash_after_cmd = cash
    inv_after_cmd = inv
    # We need to know storage after command for settlement
    storage_after_cmd = storage
    farm_after_cmd = farm
    route_after = route_established
    cmd_reason = "hold"
    # For buy, we need actual etc. For other commands, similar to turn.py

    if cmd_type == "expand_farm":
        if cash >= EXPAND_FARM_COST:
            cash_after_cmd = cash - EXPAND_FARM_COST
            farm_after_cmd = farm + EXPAND_FARM_DELTA
            cmd_reason = "expand_farm"
            success = True
        else:
            cmd_reason = "insufficient_cash_for_expand"
            success = False
        # inventory unchanged
        inv_after_cmd = inv
    elif cmd_type == "build_granary":
        if cash >= BUILD_GRANARY_COST:
            cash_after_cmd = cash - BUILD_GRANARY_COST
            storage_after_cmd = storage + BUILD_GRANARY_DELTA
            cmd_reason = "build_granary"
            success = True
        else:
            cmd_reason = "insufficient_cash_for_granary"
            success = False
        inv_after_cmd = inv
    elif cmd_type == "secure_route":
        if route_established:
            cmd_reason = "already_established"
            success = False
            # route stays True
            route_after = True
        else:
            if cash >= ROUTE_ESTABLISH_COST:
                cash_after_cmd = cash - ROUTE_ESTABLISH_COST
                route_after = True
                cmd_reason = "secure_route"
                success = True
            else:
                cmd_reason = "insufficient_cash_for_route"
                success = False
        inv_after_cmd = inv
    elif cmd_type == "buy_grain":
        cash_after_cmd, inv_after_cmd, actual, cost, cmd_reason = resolve_buy(
            cash=cash,
            price_milli=home_pre,
            storage_capacity=storage,
            inventory=inv,
            requested=requested_qty,
        )
        # Success means actual>0 and not blocked by zero? Consider actual==0 as failure for headline
        if actual <= 0:
            success = False
        else:
            success = True
        # storage unchanged (build would have changed but buy doesn't)
        storage_after_cmd = storage
        farm_after_cmd = farm
        route_after = route_established
    elif cmd_type == "ship_grain":
        # Ship command doesn't change cash/inv at command phase; settlement will handle
        # But we need to track that this is a ship intention; success depends on route etc.
        # For scoring we already have established check in capital; but for execution check again
        if not route_established:
            success = False
        else:
            # success will be determined after shipment clamping (effective>0)
            # keep as tentative True; adjust after
            success = True  # will refine after shipment resolution
        # No immediate cash/inventory change
        cash_after_cmd = cash
        inv_after_cmd = inv
        storage_after_cmd = storage
        farm_after_cmd = farm
        route_after = route_established
    else:  # hold or unknown
        success = True
        cash_after_cmd = cash
        inv_after_cmd = inv
        storage_after_cmd = storage
        farm_after_cmd = farm
        route_after = route_established

    # Production — same drought rule as player, uses post-command farm
    farm_output, _, _ = compute_farm_output(farm_after_cmd, world_now)

    # Settlement — harvest into inventory (shared primitive)
    inv_before_settlement = inv_after_cmd
    inv_final_pre_ship, settle_delta, settle_reason = resolve_storage_settlement(
        inventory_before=inv_before_settlement,
        farm_output=farm_output,
        storage_capacity=storage_after_cmd,
    )

    # Shipment — if ship_grain and route established, use resolved River price
    ship_effective = 0
    ship_delivered = 0
    ship_revenue = 0
    ship_cost = 0
    trade_cash = 0
    inv_final = inv_final_pre_ship
    ship_reason = "no_shipment"
    if cmd_type == "ship_grain" and route_established:
        # Use shared shipment primitive — resolves with correct timing
        (
            ship_effective,
            ship_delivered,
            ship_revenue,
            ship_cost,
            trade_cash,
            inv_final,
            ship_reason,
        ) = resolve_shipment(
            requested=requested_qty,
            route_established=True,
            route_capacity=settlement.route_capacity,
            route_reliability_bps=settlement.reliability_bps,
            transport_cost_per_unit=settlement.transport_cost_per_unit,
            inventory_final_pre_ship=inv_final_pre_ship,
            cash=cash_after_cmd,
            river_price=river_resolved,
        )
        # Update success based on effective
        if ship_effective <= 0:
            success = False
            # Map to blocked headline will be handled; reason already no_route/access etc but we have ship_reason
            # If ship_reason is no_route_access keep blocked
        else:
            success = True
    elif cmd_type == "ship_grain" and not route_established:
        success = False
        ship_effective = 0
        inv_final = inv_final_pre_ship

    # Cash final: for ship, cash_after_ship = cash_after_cmd + trade_cash
    # For non-ship, cash_final = cash_after_cmd (harvest etc no cash)
    if cmd_type == "ship_grain" and route_established:
        cash_final = cash_after_cmd + trade_cash
        if cash_final < 0:
            cash_final = 0
    else:
        cash_final = cash_after_cmd

    # Final rival state
    after = RivalState(
        cash=cash_final,
        inventory=InventoryState(grain=inv_final),
        farm_capacity=farm_after_cmd,
        storage_capacity=storage_after_cmd,
        route_established=route_after,
    )

    # Wealth accounting — mirror player decomposition
    wealth_before = before.cash + value_for(before.inventory.grain, home_pre)
    wealth_after = after.cash + value_for(after.inventory.grain, home_resolved)
    # Quantity value at pre price
    quantity_value_effect = value_for(after.inventory.grain, home_pre) - value_for(
        before.inventory.grain, home_pre
    )
    # Price value at final inventory
    price_value_effect = value_for(after.inventory.grain, home_resolved) - value_for(
        after.inventory.grain, home_pre
    )
    cash_effect = after.cash - before.cash
    wealth_delta = cash_effect + quantity_value_effect + price_value_effect
    # Sanity: must match wealth_after - wealth_before
    assert wealth_after - wealth_before == wealth_delta, (
        f"rival wealth mismatch {wealth_after}-{wealth_before} vs {wealth_delta}"
    )

    inventory_delta = after.inventory.grain - before.inventory.grain

    # Headline — truthful from resolved after state vs before
    # For blocked expand/build/ship, success flag already false
    headline = _headline_for(profile, command, before, after, success)

    return RivalTurnResult(
        rival_id=profile.id,
        before=before,
        command=command,
        after=after,
        headline=headline,
        cash_delta=after.cash - before.cash,
        inventory_delta=inventory_delta,
        cash_effect=cash_effect,
        quantity_value_effect=quantity_value_effect,
        price_value_effect=price_value_effect,
        wealth_delta=wealth_delta,
        wealth_before=wealth_before,
        wealth_after=wealth_after,
    )


def rival_wealth(state: RivalState, home_price: int) -> int:
    """Wealth = cash + inventory value at home_price."""
    return state.cash + value_for(state.inventory.grain, home_price)
