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

from app.domain.types import InventoryState, Money, PlayerCommand, Quantity, WorldCondition
from app.engine.actor import (
    BUILD_GRANARY_COST,
    EXPAND_FARM_COST,
    EXPAND_FARM_DELTA,
    ROUTE_ESTABLISH_COST,
    YIELD_PER_CAPACITY,
    compute_farm_output,
    cost_for_quantity,
    resolve_build_granary,
    resolve_buy,
    resolve_expand_farm,
    resolve_secure_route,
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
ExposureTag = Literal["farm_penalize", "farm_reward"]


class RivalPreferences(BaseModel):
    """Immutable preference vector — bps per command, frozen so profile cannot mutate."""

    model_config = ConfigDict(frozen=True)

    expand_farm: int = Field(ge=0, description="Pref bps for expand_farm")
    build_granary: int = Field(ge=0, description="Pref bps for build_granary")
    buy_grain: int = Field(ge=0, description="Pref bps for buy_grain")
    hold: int = Field(ge=0, description="Pref bps for hold")
    secure_route: int = Field(ge=0, description="Pref bps for secure_route")
    ship_grain: int = Field(ge=0, description="Pref bps for ship_grain")

    def get(self, key: str, default: int = 10000) -> int:
        return getattr(self, key, default) if hasattr(self, key) else default


class RivalProfile(BaseModel):
    """Personality — preferences and risk, not economic state."""

    model_config = ConfigDict(frozen=True)

    id: RivalId = Field(description="Rival identity")
    preferences_bps: RivalPreferences = Field(description="Preference per command type in bps")
    risk_cash_floor: Money = Field(description="Cash floor for risk penalty")
    risk_penalty_bps: int = Field(description="Risk multiplier when cash would drop below floor")
    exposure_tag: ExposureTag = Field(description="farm_penalize or farm_reward")


class RivalState(BaseModel):
    """Economic state — cash/inventory/capacities/route, no headline."""

    model_config = ConfigDict(frozen=True)

    cash: Money = Field(description="Rival cash")
    inventory: InventoryState = Field(description="Rival grain inventory")
    farm_capacity: Quantity = Field(description="Farm capacity")
    storage_capacity: Quantity = Field(description="Storage capacity")
    route_established: bool = Field(description="River route established for rival")


class RivalTurnResult(BaseModel):
    """Structured outcome for one rival on one turn."""

    model_config = ConfigDict(frozen=True)

    rival_id: RivalId = Field(description="Which rival")
    before: RivalState = Field(description="State before turn")
    command: PlayerCommand = Field(description="Chosen command")
    after: RivalState = Field(description="State after turn")
    headline: str = Field(description="Truthful headline derived from resolved outcome")
    reason_code: str = Field(description="Machine reason code from resolved execution")
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
MIRA_PREFERENCES = RivalPreferences(
    expand_farm=4500,
    build_granary=15000,
    buy_grain=13000,
    hold=10000,
    secure_route=14500,
    ship_grain=12000,
)
DARAN_PREFERENCES = RivalPreferences(
    expand_farm=16000,
    build_granary=7000,
    buy_grain=11000,
    hold=10000,
    secure_route=6000,
    ship_grain=5000,
)

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

# Headline templates — truthful, derived from resolved reason_code (not bool success)
# Every reason_code produced by shared actor primitives has a truthful mapping.
# Partial successes (limited_by_capacity, ship_limited) still report shipped.
HEADLINES_BY_REASON: dict[str, dict[str, str]] = {
    "mira": {
        "expand_farm": "Mira expanded her farm holdings.",
        "insufficient_cash_for_expand": "Mira is short of cash after recent investments.",
        "build_granary": "Mira leased additional storage.",
        "insufficient_cash_for_granary": "Mira is short of cash and could not lease storage.",
        "buy_grain": "Mira accumulated grain reserves.",
        "insufficient_cash": "Mira is short of cash and could not buy grain.",
        "insufficient_storage": "Mira's granaries are full and could not buy more grain.",
        "buy_grain_zero": "Mira tried to buy grain but could not.",
        "secure_route": "Mira secured capacity on the river route.",
        "already_established": "Mira already has river access.",
        "insufficient_cash_for_route": "Mira is short of cash and could not secure the river route.",
        "ship_grain": "Mira shipped grain to River Town.",
        "limited_by_capacity": "Mira shipped grain to River Town.",
        "ship_limited": "Mira shipped grain to River Town.",
        "insufficient_inventory": "Mira wanted to ship grain but had insufficient grain.",
        "insufficient_cash_for_transport": "Mira is short of cash for transport and could not ship.",
        "no_route_access": "Mira wanted to ship grain but lacked route access.",
        "hold": "Mira is conserving cash.",
        "no_shipment": "Mira is conserving cash.",
    },
    "daran": {
        "expand_farm": "Daran bought another large tract of farmland.",
        "insufficient_cash_for_expand": "Daran is short of cash after expanding aggressively.",
        "build_granary": "Daran added granary capacity.",
        "insufficient_cash_for_granary": "Daran is short of cash and could not build a granary.",
        "buy_grain": "Daran stockpiled grain.",
        "insufficient_cash": "Daran is short of cash and could not buy grain.",
        "insufficient_storage": "Daran's granaries are full and could not buy more grain.",
        "buy_grain_zero": "Daran tried to buy grain but could not.",
        "secure_route": "Daran secured river access.",
        "already_established": "Daran already has river access.",
        "insufficient_cash_for_route": "Daran is short of cash and could not secure the route.",
        "ship_grain": "Daran shipped grain to River Town.",
        "limited_by_capacity": "Daran shipped grain to River Town.",
        "ship_limited": "Daran shipped grain to River Town.",
        "insufficient_inventory": "Daran wanted to ship grain but had insufficient grain.",
        "insufficient_cash_for_transport": "Daran is short of cash for transport and could not ship.",
        "no_route_access": "Daran wanted to ship grain but lacked route access.",
        "hold": "Daran held his position.",
        "no_shipment": "Daran held his position.",
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
        est = (YIELD_PER_CAPACITY * EXPAND_FARM_DELTA * home // 1000 * 2) - EXPAND_FARM_COST
        # Diminishing for Mira when storage is ample and no threat — farm scale less urgent
        if profile.id == "mira" and obs.next_world_known is None:
            farm_out, _, _ = compute_farm_output(cap, obs.world_now)
            projected = inv + farm_out * 2
            if projected < storage * 60 // 100:  # ample
                est = (
                    est * 35 // 100
                )  # Mira values farm much less when not threatened and storage ample
        return max(0, est)
    if cmd_type == "build_granary":
        farm_out, _, _ = compute_farm_output(cap, obs.world_now)
        projected = inv + farm_out * 2
        # Strong diminishing marginal utility: once projected safely below storage, extra granary is low value
        # Use integer thresholds to avoid float.
        if projected > storage:
            tier = "tight"
        elif projected > storage * 85 // 100:
            tier = "near_full"
        elif projected > storage * 60 // 100:
            tier = "mid"
        else:
            tier = "ample"
        if tier == "tight":
            base = 340 if profile.id == "mira" else 220
        elif tier == "near_full":
            base = 180 if profile.id == "mira" else 90
        elif tier == "mid":
            base = 80 if profile.id == "mira" else 30
        else:  # ample — safely below, very small diminishing return
            base = 25 if profile.id == "mira" else 12
        if obs.next_world_known == "drought":
            if profile.id == "mira":
                base = base * 14 // 10  # Mira +40% for threat (still small if ample)
            else:
                base = base * 11 // 10
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
        # Without threat, Mira still values route option modestly when storage is ample (flexibility)
        # This lets trade identity show even without warning.
        if est_per <= 0:
            if profile.id == "mira":
                # Ample storage → route more attractive than farm for Mira
                farm_out, _, _ = compute_farm_output(cap, obs.world_now)
                projected = inv + farm_out * 2
                if projected < storage * 60 // 100:
                    return max(0, 220)  # Mira values flexibility when not farm-constrained
                est_per = 70
            else:
                est_per = 40
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
    reason_code: str,
) -> str:
    """Derive truthful headline from reason_code, not bool success."""
    pid = profile.id
    return HEADLINES_BY_REASON[pid].get(
        reason_code, HEADLINES_BY_REASON[pid].get("hold", "Rival acted.")
    )


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

    cash_after_cmd = cash
    inv_after_cmd = inv
    storage_after_cmd = storage
    farm_after_cmd = farm
    route_after = route_established
    cmd_reason = "hold"
    # For buy we track actual for later reason handling
    buy_actual = 0

    if cmd_type == "expand_farm":
        cash_after_cmd, farm_after_cmd, _delta, cmd_reason = resolve_expand_farm(
            cash=cash, farm_capacity=farm
        )
        inv_after_cmd = inv
    elif cmd_type == "build_granary":
        cash_after_cmd, storage_after_cmd, _delta, cmd_reason = resolve_build_granary(
            cash=cash, storage_capacity=storage
        )
        inv_after_cmd = inv
    elif cmd_type == "secure_route":
        cash_after_cmd, route_after, _delta, cmd_reason = resolve_secure_route(
            cash=cash, route_established=route_established
        )
        inv_after_cmd = inv
    elif cmd_type == "buy_grain":
        cash_after_cmd, inv_after_cmd, buy_actual, _cost, cmd_reason = resolve_buy(
            cash=cash,
            price_milli=home_pre,
            storage_capacity=storage,
            inventory=inv,
            requested=requested_qty,
        )
        storage_after_cmd = storage
        farm_after_cmd = farm
        route_after = route_established
    elif cmd_type == "ship_grain":
        # Ship intent — settlement will determine actual; keep cmd_reason as ship_grain for now
        # Actual reason will be ship_reason after settlement; use placeholder
        cmd_reason = "ship_grain" if route_established else "no_route_access"
        cash_after_cmd = cash
        inv_after_cmd = inv
        storage_after_cmd = storage
        farm_after_cmd = farm
        route_after = route_established
    else:  # hold or unknown
        cmd_reason = "hold"
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
    elif cmd_type == "ship_grain" and not route_established:
        ship_reason = "no_route_access"
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

    # Headline — truthful from resolved reason_code, not bool success
    # For ship commands the reason is ship_reason, otherwise cmd_reason
    final_reason = ship_reason if cmd_type == "ship_grain" else cmd_reason
    headline = _headline_for(profile, final_reason)

    return RivalTurnResult(
        rival_id=profile.id,
        before=before,
        command=command,
        after=after,
        headline=headline,
        reason_code=final_reason,
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
