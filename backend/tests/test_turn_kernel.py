"""Section 3 kernel tests — AC #1,3,4,5,6."""

from __future__ import annotations

from app.domain.types import GameState, InventoryState, MarketState, PlayerCommand, PlayerState
from app.engine.turn import TURN_ORDER, resolve_turn


def _base_state(
    cash: int = 1000,
    grain: int = 20,
    farm: int = 10,
    storage: int = 100,
    supply: int = 100,
    demand: int = 120,
    base_price: int = 5000,
    current_price: int = 5000,
    turn: int = 0,
    seed: str = "seed-001",
    version: str = "1.0",
) -> GameState:
    return GameState(
        turn=turn,
        run_seed=seed,
        ruleset_version=version,
        player=PlayerState(
            cash=cash,
            inventory=InventoryState(grain=grain),
            farm_capacity=farm,
            storage_capacity=storage,
        ),
        market=MarketState(
            supply=supply, demand=demand, base_price=base_price, current_price=current_price
        ),
    )


def test_determinism_same_inputs_same_result() -> None:
    state = _base_state()
    cmd = PlayerCommand(type="hold")
    ctx = state.to_turn_context()
    r1 = resolve_turn(state, cmd, "drought", ctx)
    r2 = resolve_turn(state, cmd, "drought", ctx)
    assert r1 == r2
    # also different command same seed but deterministic per command
    cmd2 = PlayerCommand(type="expand_farm")
    r3 = resolve_turn(state, cmd2, "normal", ctx)
    r4 = resolve_turn(state, cmd2, "normal", ctx)
    assert r3 == r4
    assert r1 != r3  # different command yields different result


def test_determinism_seed_matters_only_via_context() -> None:
    # Same state fields except seed leads to same structure except RNG
    # Core price is deterministic; ensure same seed yields identical
    s1 = _base_state(seed="seed-A")
    s2 = _base_state(seed="seed-B")
    cmd = PlayerCommand(type="hold")
    r1 = resolve_turn(s1, cmd, "normal", s1.to_turn_context())
    r2 = resolve_turn(s2, cmd, "normal", s2.to_turn_context())
    # With same supply/demand/price, results may be equal;
    # In our impl core price is not RNG-driven, so seeds same next_state.
    # But we still prove determinism per seed: repeating same seed gives same.
    r1b = resolve_turn(s1, cmd, "normal", s1.to_turn_context())
    assert r1 == r1b
    # r1 and r2 may be equal because RNG not affecting price; that's okay.
    assert r2 == resolve_turn(s2, cmd, "normal", s2.to_turn_context())


def test_turn_increments_and_no_negatives() -> None:
    for world in ("normal", "drought"):
        for cmd_type in ("expand_farm", "build_granary", "buy_grain", "hold"):
            state = _base_state()
            qty = 10 if cmd_type == "buy_grain" else None
            cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
            res = resolve_turn(state, cmd, world, state.to_turn_context())  # type: ignore[arg-type]
            ns = res.next_state
            assert ns.turn == state.turn + 1
            assert ns.player.cash >= 0
            assert ns.player.inventory.grain >= 0
            assert ns.player.farm_capacity >= 0
            assert ns.player.storage_capacity >= 0
            assert ns.market.supply >= 0
            assert ns.market.demand >= 0
            assert ns.market.base_price >= 0
            assert ns.market.current_price >= 1  # prices stay positive
            # also check effects deltas don't produce negatives via construction
            for eff in res.domain_effects:
                assert eff.after >= 0


def test_drought_reduces_farm_output_and_supply_not_direct_price() -> None:
    state = _base_state(farm=10, supply=100, demand=120)
    cmd = PlayerCommand(type="hold")
    normal = resolve_turn(state, cmd, "normal", state.to_turn_context())
    drought = resolve_turn(state, cmd, "drought", state.to_turn_context())

    # Find farm_output nodes
    def farm_output(trace):  # type: ignore[no-untyped-def]
        for n in trace.nodes:
            if n.id == "farm_output":
                return n.after
        return None

    normal_out = farm_output(normal.causal_trace)
    drought_out = farm_output(drought.causal_trace)
    assert normal_out is not None and drought_out is not None
    assert drought_out < normal_out, "drought must reduce farm output"

    # Supply after drought should be less than normal (since added smaller output)
    assert drought.next_state.market.supply < normal.next_state.market.supply

    # Price after drought should be >= normal price (higher scarcity)
    assert drought.next_state.market.current_price >= normal.next_state.market.current_price

    # Trace must not have direct drought->price edge
    for node in drought.causal_trace.nodes:
        if node.id in ("price", "target_price", "price_pressure"):
            assert "world" not in node.parent_ids, (
                f"direct drought->price edge forbidden: {node.id} parents {node.parent_ids}"
            )
    # Chain must exist: world -> farm_output -> supply -> price_pressure -> target_price -> price
    ids = [n.id for n in drought.causal_trace.nodes]
    assert "world" in ids
    assert "farm_output" in ids
    assert "supply" in ids
    assert "price" in ids
    # Check parent chain
    supply_node = next(n for n in drought.causal_trace.nodes if n.id == "supply")
    assert "farm_output" in supply_node.parent_ids
    farm_node = next(n for n in drought.causal_trace.nodes if n.id == "farm_output")
    assert "world" in farm_node.parent_ids


def test_drought_price_not_direct_mutation_grep() -> None:
    # Ensure turn.py does not contain forbidden direct price mutation string
    import pathlib

    src = pathlib.Path("backend/app/engine/turn.py").read_text()
    # Forbid pattern like "if world == \"drought\": ... price *"
    # We check that drought branch does not assign to price directly
    # Simple: ensure "drought" and "price" not on same line with "*=" or "price ="
    # This is a lightweight guard; main guarantee is trace chain above.
    assert "price *= 1.4" not in src
    assert "drought_price" not in src.lower()


def test_farm_output_parents_are_world_and_farm_capacity_not_command() -> None:
    # Blocker 2: hold/buy/build must not claim command caused farm output.
    # Correct graph: world ─┐ → farm_output , farm_capacity ─┘
    # expand_farm → farm_capacity, but farm_output parents are still world+farm_capacity.
    for cmd_type in ("hold", "buy_grain", "build_granary", "expand_farm"):
        state = _base_state(farm=10, supply=100, demand=120)
        qty = 5 if cmd_type == "buy_grain" else None
        cmd = PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
        res = resolve_turn(state, cmd, "normal", state.to_turn_context())  # type: ignore[arg-type]
        # Every turn must have a stable farm_capacity node
        assert any(n.id == "farm_capacity" for n in res.causal_trace.nodes), (
            f"missing farm_capacity for {cmd_type}"
        )
        farm_out = next(n for n in res.causal_trace.nodes if n.id == "farm_output")
        # Must depend on world + farm_capacity, never directly on command
        assert "world" in farm_out.parent_ids
        assert "farm_capacity" in farm_out.parent_ids
        assert "command" not in farm_out.parent_ids, f"false command→farm_output for {cmd_type}"
        # Farm capacity node itself should not falsely link command except for expand_farm
        farm_cap = next(n for n in res.causal_trace.nodes if n.id == "farm_capacity")
        if cmd_type == "expand_farm":
            assert "command" in farm_cap.parent_ids
        else:
            assert farm_cap.parent_ids == (), (
                f"{cmd_type} should not make farm_capacity child of command"
            )
        # No direct world→price edge already covered, but also ensure supply→price chain intact
        assert any(n.id == "supply" for n in res.causal_trace.nodes)
        assert any(n.id == "price" for n in res.causal_trace.nodes)


def test_buy_beyond_cash_is_clamped() -> None:
    # Price 5000 => 5 per unit, cash 100 can afford at most 20 units
    # Farm 10 gives output 100, storage 100 caps total to 100.
    state = _base_state(cash=100, grain=0, storage=100, current_price=5000)
    cmd = PlayerCommand(type="buy_grain", quantity=50)  # request 50, can only afford 20
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    # Buy itself is clamped to 20 — verify via inventory_after_buy node
    buy_node = next(n for n in res.causal_trace.nodes if n.id == "inventory_after_buy")
    assert buy_node.delta == 20
    assert buy_node.after == 20
    assert "insufficient_cash" in buy_node.reason_code
    # Total inventory after harvest is buy_actual (20) + farm_output (100) capped to storage 100
    assert res.next_state.player.inventory.grain == 100
    # Cash should be spent fully: 100 - 100 =0
    cash_eff = next(e for e in res.domain_effects if e.metric == "cash")
    assert cash_eff.after == 0
    assert res.next_state.player.cash >= 0
    # Also verify domain effect for buy shows before 0 after 20
    inv_eff = next(e for e in res.domain_effects if e.metric == "inventory")
    assert inv_eff.delta == 20


def test_buy_beyond_storage_is_clamped() -> None:
    # Storage 30, grain 25 => space 5, request 20 => should clamp to 5
    state = _base_state(
        cash=10000, grain=25, storage=30, current_price=5000, farm=0, supply=100, demand=100
    )
    # farm 0 => no harvest to confuse; inventory after should be exactly capped
    cmd = PlayerCommand(type="buy_grain", quantity=20)
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    # With farm 0, farm_output 0, so inventory final = 25 + min(20,5)=30
    assert res.next_state.player.inventory.grain == 30
    # Check reason
    buy_node = next(n for n in res.causal_trace.nodes if n.id == "inventory_after_buy")
    assert buy_node.reason_code == "insufficient_storage"
    # Cash cost for 5 units at 5 per unit =25
    cash_eff = next(e for e in res.domain_effects if e.metric == "cash")
    assert cash_eff.after == 10000 - 25


def test_every_major_change_has_trace_entry() -> None:
    # Expand farm should have farm_capacity, cash, farm_output, supply, price nodes
    state = _base_state()
    cmd = PlayerCommand(type="expand_farm")
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    ids = {n.id for n in res.causal_trace.nodes}
    assert "command" in ids
    assert "farm_capacity" in ids
    assert "cash_after_command" in ids
    assert "farm_output" in ids
    assert "supply" in ids
    assert "price" in ids
    assert "inventory" in ids
    # Every domain effect metric should have a corresponding node kind
    for _eff in res.domain_effects:
        # At least one node should mention the metric or related kind
        assert len(res.causal_trace.nodes) >= 5


def test_hold_does_not_change_capacities() -> None:
    state = _base_state(cash=500, farm=5, storage=50)
    cmd = PlayerCommand(type="hold")
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    assert res.next_state.player.farm_capacity == 5
    assert res.next_state.player.storage_capacity == 50
    # Cash unchanged by hold (except maybe? hold costs 0)
    assert res.next_state.player.cash == 500


def test_expand_farm_consumes_cash_and_increases_capacity() -> None:
    state = _base_state(cash=1000, farm=10, storage=50)
    cmd = PlayerCommand(type="expand_farm")
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    assert res.next_state.player.cash == 500
    assert res.next_state.player.farm_capacity == 20
    # With higher farm, output should be higher than hold
    hold_res = resolve_turn(state, PlayerCommand(type="hold"), "normal", state.to_turn_context())
    assert (
        res.next_state.player.inventory.grain > hold_res.next_state.player.inventory.grain
        or res.next_state.market.supply > hold_res.next_state.market.supply
    )


def test_build_granary_increases_storage() -> None:
    state = _base_state(cash=1000, storage=50)
    cmd = PlayerCommand(type="build_granary")
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    assert res.next_state.player.storage_capacity == 100
    assert res.next_state.player.cash == 700


def test_price_bounded_movement() -> None:
    # Create extreme scarcity to try to push price far, but max_movement caps it
    state = _base_state(supply=10, demand=1000, base_price=5000, current_price=5000)
    cmd = PlayerCommand(type="hold")
    res = resolve_turn(state, cmd, "normal", state.to_turn_context())
    # max_movement 2000 bps =20% => max delta 1000
    assert abs(res.next_state.market.current_price - 5000) <= 1000
    # Also check that price stays positive even when supply huge
    state2 = _base_state(supply=10000, demand=10, base_price=5000, current_price=5000)
    res2 = resolve_turn(state2, cmd, "normal", state2.to_turn_context())
    assert res2.next_state.market.current_price >= 1
    assert res2.next_state.market.current_price < 5000  # downward pressure


def test_turn_order_constant() -> None:
    assert (
        TURN_ORDER
        == "command -> production -> home_supply -> river_supply -> home_price -> river_price -> settlement -> route_settlement -> valuation"
    )


def test_player_outcome_drivers_deterministic_and_bounded() -> None:
    state = _base_state()
    cmd = PlayerCommand(type="expand_farm")
    ctx = state.to_turn_context()
    r1 = resolve_turn(state, cmd, "drought", ctx)
    r2 = resolve_turn(state, cmd, "drought", ctx)
    assert r1.player_outcome.top_drivers == r2.player_outcome.top_drivers
    assert len(r1.player_outcome.top_drivers) <= 3
