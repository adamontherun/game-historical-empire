"""Mappers: FiveTurnGame -> GameView. Pure, no mutation."""

from __future__ import annotations

from app.api.schemas import (
    ChoiceView,
    CompletionSummaryView,
    EmpireSummary,
    GameView,
    MarketView,
    OutcomeView,
    PlayerSummary,
    RivalHeadlines,
    RouteStatus,
)
from app.api.sessions import GameSession
from app.domain.types import GameState, MarketState, PlayerCommand
from app.engine.actor import (
    BUILD_GRANARY_COST,
    EXPAND_FARM_COST,
    ROUTE_ESTABLISH_COST,
    affordable_quantity,
    compute_farm_output,
    cost_for_quantity,
    ship_margin,
    value_for,
)
from app.engine.pressure import PRESSURE_ARC, pressure_for_turn
from app.engine.prototype import TURN_LIMIT, FiveTurnGame


def _wealth(state: GameState) -> int:
    return state.player.cash + value_for(state.player.inventory.grain, state.market.current_price)


def _market_view(m: MarketState) -> MarketView:
    return MarketView(
        supply=m.supply,
        demand=m.demand,
        base_price=m.base_price,
        current_price=m.current_price,
        responsiveness=m.responsiveness,
    )


def choices_for(session: GameSession) -> tuple[ChoiceView, ...]:
    """Legality + affordability ONLY (B1). No turn gating, no margin>0 gating.

    Two quantities per verb (partial+full, ~6-8 total).
    Harness policies never influence this — measuring instrument, not rules.
    """
    s = session.game.state
    out: list[ChoiceView] = []
    # hold always
    out.append(
        ChoiceView(id="hold", label="Hold — preserve cash", kind="hold", quantity=None, cost=0)
    )
    if s.player.cash >= EXPAND_FARM_COST:
        out.append(
            ChoiceView(
                id="expand_farm",
                label="Expand farm — 500 cash → +10 capacity",
                kind="expand_farm",
                quantity=None,
                cost=EXPAND_FARM_COST,
            )
        )
    if s.player.cash >= BUILD_GRANARY_COST:
        out.append(
            ChoiceView(
                id="build_granary",
                label="Build granary — 300 cash → +50 storage",
                kind="build_granary",
                quantity=None,
                cost=BUILD_GRANARY_COST,
            )
        )
    if not s.route.established and s.player.cash >= ROUTE_ESTABLISH_COST:
        out.append(
            ChoiceView(
                id="secure_route",
                label="Secure river route — 400 cash",
                kind="secure_route",
                quantity=None,
                cost=ROUTE_ESTABLISH_COST,
            )
        )
    # buy_grain: ANY turn, if headroom>0 — two options (partial+full)
    # B2 engine-agreement: clamp on actual engine rule storage - inventory
    # 80 is buy cap (Section 9 tuning, keeps trade profitable within price band)
    space = s.player.storage_capacity - s.player.inventory.grain
    price = s.market.current_price
    if price > 0:
        affordable = affordable_quantity(s.player.cash, price, 10_000_000)
        max_buy = min(max(space, 0), affordable, 80)
        if max_buy > 0:
            qtys = {max_buy, max(1, max_buy // 2)}
            for qty in sorted(qtys):
                cost = cost_for_quantity(qty, price)
                out.append(
                    ChoiceView(
                        id=f"buy_grain:{qty}",
                        label=f"Buy {qty} grain — {cost} cash",
                        kind="buy_grain",
                        quantity=qty,
                        cost=cost,
                    )
                )
    # sell_grain: ANY turn, if inventory>0 — two options (150 cap avoids dumping entire store at once)
    if s.player.inventory.grain > 0:
        n = min(s.player.inventory.grain, 150)
        qtys_s = {n, max(1, n // 2)}
        for qty in sorted(qtys_s):
            out.append(
                ChoiceView(
                    id=f"sell_grain:{qty}",
                    label=f"Sell {qty} grain",
                    kind="sell_grain",
                    quantity=qty,
                    cost=None,
                )
            )
    # ship_grain: if established & inventory>0 — TWO options, no margin gate (B1)
    if s.route.established and s.player.inventory.grain > 0:
        # B2: pre-ship inventory includes harvest that lands before shipment
        # Estimate respects drought via compute_farm_output, not raw YIELD_PER_CAPACITY
        # world for this turn (decision time) — pressure derived
        curr_pressure = session.game.current_pressure
        world_for_est = curr_pressure.world if curr_pressure is not None else "normal"
        farm_output_est, _, _ = compute_farm_output(s.player.farm_capacity, world_for_est)
        pre_ship = s.player.inventory.grain + farm_output_est
        # cap by storage (harvest may be capped)
        if pre_ship > s.player.storage_capacity:
            pre_ship = s.player.storage_capacity
        cap = min(pre_ship, s.route.capacity)
        if cap > 0:
            qtys_sh = {cap, max(1, cap // 2)}
            for qty in sorted(qtys_sh):
                out.append(
                    ChoiceView(
                        id=f"ship_grain:{qty}",
                        label=f"Ship {qty} grain to River Town",
                        kind="ship_grain",
                        quantity=qty,
                        cost=None,
                    )
                )
    return tuple(out)


def _outcome_view(session: GameSession) -> OutcomeView | None:
    game = session.game
    if not game.history:
        return None
    idx = len(game.history) - 1
    res = game.history[idx]
    pressure = PRESSURE_ARC[idx]
    title = pressure.title
    # Use stored command from session.commands — not trace label parsing (C4)
    if session.commands and idx < len(session.commands):
        cmd: PlayerCommand = session.commands[idx]
        cmd_type = cmd.type
        cmd_qty = cmd.quantity
    else:
        # fallback to trace parsing if commands missing (should not happen)
        cmd_node = next((n for n in res.causal_trace.nodes if n.id == "command"), None)
        cmd_type = "hold"
        cmd_qty = None
        if cmd_node is not None:
            lbl = cmd_node.label.lower()
            for verb in (
                "expand_farm",
                "build_granary",
                "buy_grain",
                "sell_grain",
                "secure_route",
                "ship_grain",
                "hold",
            ):
                if verb in lbl.replace(" ", "_") or verb.replace("_", " ") in lbl:
                    cmd_type = verb
                    break
            if cmd_node.delta is not None and cmd_node.kind == "command":
                if "requested=" in cmd_node.label:
                    try:
                        part = cmd_node.label.split("requested=")[1].split()[0].strip(",")
                        cmd_qty = int(part)
                    except Exception:
                        cmd_qty = cmd_node.delta if cmd_node.delta != 0 else None
                else:
                    cmd_qty = cmd_node.delta if cmd_node.delta != 0 else None
                if cmd_qty == 0:
                    cmd_qty = None

    return OutcomeView(
        resolved_turn=idx,
        title=title,
        pressure_stage=pressure.stage,
        world=pressure.world,
        command_type=cmd_type,
        command_quantity=cmd_qty,
        wealth_delta=res.player_outcome.wealth_delta,
        inventory_delta=res.player_outcome.inventory_delta,
        price_delta=res.player_outcome.price_delta,
        drivers=res.player_outcome.drivers,
        domain_effects=res.domain_effects,
        causal_trace=res.causal_trace,
    )


def _completion_summary(session: GameSession) -> CompletionSummaryView | None:
    game = session.game
    if not game.is_complete:
        return None
    # summary is available via game.summary() but that returns StrategicSummary with history — do NOT expose it.
    # Build CompletionSummaryView from game state directly (C3).
    summary = game.summary()
    # final rival headlines as pre-rendered strings (no raw states)
    headlines: RivalHeadlines | None = None
    if game.rival_history:
        mira_res, daran_res = game.rival_history[-1]
        headlines = RivalHeadlines(mira=mira_res.headline, daran=daran_res.headline)
    elif summary.final_rivals is not None:
        # fallback if history empty but rivals exist — use current rivals?
        headlines = RivalHeadlines(
            mira=f"Mira cash {summary.final_rivals[0].cash}",
            daran=f"Daran cash {summary.final_rivals[1].cash}",
        )
    return CompletionSummaryView(
        initial_wealth=summary.initial_wealth,
        final_wealth=summary.final_wealth,
        wealth_delta_total=summary.wealth_delta_total,
        final_cash=game.state.player.cash,
        final_grain=game.state.player.inventory.grain,
        final_farm_capacity=game.state.player.farm_capacity,
        final_storage_capacity=game.state.player.storage_capacity,
        cash_low=summary.cash_low,
        peak_inventory=summary.peak_inventory,
        is_complete=True,
        final_rival_headlines=headlines,
    )


def to_game_view(session: GameSession) -> GameView:
    game: FiveTurnGame = session.game
    state = game.state
    # top-level = NEXT decision context (C4); when complete, keep aftermath for display
    if game.is_complete:
        signal = PRESSURE_ARC[-1].signal
        pressure_stage = PRESSURE_ARC[-1].stage
        world = PRESSURE_ARC[-1].world
    else:
        idx = len(game.history)
        p = pressure_for_turn(idx)
        signal = p.signal
        pressure_stage = p.stage
        world = p.world

    # Build rival headlines (latest)
    rival_headlines: RivalHeadlines | None = None
    if game.rival_history:
        m, d = game.rival_history[-1]
        rival_headlines = RivalHeadlines(mira=m.headline, daran=d.headline)

    # Choices — empty when complete (no more decisions)
    if game.is_complete:
        available: tuple[ChoiceView, ...] = ()
    else:
        available = choices_for(session)

    # Wealth
    wealth = _wealth(state)

    # Route next_margin via engine helper (B6), even when negative (B1) — S0a reliability-aware
    next_margin = ship_margin(
        state.river_market.current_price,
        state.route.transport_cost_per_unit,
        state.market.current_price,
        state.route.reliability_bps,
    )

    return GameView(
        game_id=session.game_id,
        run_seed=session.run_seed,
        ruleset_version=state.ruleset_version,
        revision=session.revision,
        turn=state.turn,
        turn_limit=TURN_LIMIT,
        signal=signal,
        pressure_stage=pressure_stage,
        world=world,
        player_summary=PlayerSummary(
            cash=state.player.cash,
            inventory_grain=state.player.inventory.grain,
            farm_capacity=state.player.farm_capacity,
            storage_capacity=state.player.storage_capacity,
            wealth=wealth,
        ),
        empire_summary=EmpireSummary(
            farm_capacity=state.player.farm_capacity,
            storage_capacity=state.player.storage_capacity,
            route_established=state.route.established,
        ),
        home_valley_market=_market_view(state.market),
        river_town_market=_market_view(state.river_market),
        route_status=RouteStatus(
            established=state.route.established,
            capacity=state.route.capacity,
            transport_cost_per_unit=state.route.transport_cost_per_unit,
            reliability_bps=state.route.reliability_bps,
            next_margin=next_margin,
        ),
        rival_headlines=rival_headlines,
        available_choices=available,
        latest_outcome=_outcome_view(session),
        completion_summary=_completion_summary(session),
    )


# Helper to build choice_map for fast lookup — maps id -> PlayerCommand
def choice_map_for(session: GameSession) -> dict[str, PlayerCommand]:
    """Map choice_id -> PlayerCommand for current revision."""
    m: dict[str, PlayerCommand] = {}
    for ch in choices_for(session):
        # ch.id is like "buy_grain:40" -> type "buy_grain", quantity 40
        if ":" in ch.id:
            typ, qty_s = ch.id.split(":", 1)
            qty = int(qty_s)
            cmd = PlayerCommand.model_validate({"type": typ, "quantity": qty})
        else:
            cmd = PlayerCommand.model_validate({"type": ch.id})
        m[ch.id] = cmd
    return m
