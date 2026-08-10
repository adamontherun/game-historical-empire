"""Section 7 — Deterministic Rivals acceptance tests.

AC1: recognizably different (profile vs state, integer/bps, not start-resource artifact)
AC2: deterministic
AC3: capital constraints real (shared primitives, same costs)
AC4: no money creation (with price revaluation)
AC5: informs player choice (behavioral preparation vs concentration, not scripted T3 headline)
AC6: headlines derived and visible after first turn
Plus shared-primitive parity and isolation.
"""

from __future__ import annotations

from app.domain.types import InventoryState, PlayerCommand
from app.engine.actor import (
    BUILD_GRANARY_COST,
    BUILD_GRANARY_DELTA,
    EXPAND_FARM_COST,
    EXPAND_FARM_DELTA,
    ROUTE_ESTABLISH_COST,
    cost_for_quantity,
    value_for,
)
from app.engine.prototype import FiveTurnGame
from app.engine.rivals import (
    DARAN_PROFILE,
    MIRA_PROFILE,
    ObservableContext,
    RivalState,
    RivalTurnResult,
    SettlementContext,
    apply_rival_command,
    choose_rival_command,
    score_rival_command,
)


def _obs(
    turn: int = 0,
    world_now: str = "normal",
    next_known: str | None = None,
    home: int = 5000,
    river: int = 5200,
    seed: str = "test-seed",
    version: str = "1.0",
) -> ObservableContext:
    # type ignore for WorldCondition literal
    return ObservableContext(
        turn=turn,
        world_now=world_now,  # type: ignore[arg-type]
        next_world_known=next_known,  # type: ignore[arg-type]
        home_price_pre=home,
        river_price_pre=river,
        transport_cost_per_unit=800,
        route_capacity=20,
        reliability_bps=10000,
        home_supply=100,
        home_demand=90,
        run_seed=seed,
        ruleset_version=version,
    )


def test_profiles_differ_under_identical_state() -> None:
    """Mira vs Daran with identical RivalState must differ — proves personality."""
    identical = RivalState(
        cash=800,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    contexts = [
        _obs(turn=0, world_now="normal", next_known=None, home=4545, river=5600),
        _obs(turn=2, world_now="normal", next_known="drought", home=5000, river=6200),
        _obs(turn=3, world_now="drought", next_known=None, home=5200, river=6200),
        ObservableContext(
            turn=1,
            world_now="normal",
            next_world_known=None,
            home_price_pre=5000,
            river_price_pre=5200,
            transport_cost_per_unit=800,
            route_capacity=20,
            reliability_bps=10000,
            home_supply=80,
            home_demand=90,
            run_seed="s",
            ruleset_version="1.0",
        ),
        _obs(turn=1, world_now="normal", next_known=None, home=5000, river=5200),
    ]
    # use tight state for last context
    states = [
        identical,
        identical,
        identical,
        RivalState(
            cash=100,
            inventory=InventoryState(grain=20),
            farm_capacity=10,
            storage_capacity=200,
            route_established=False,
        ),
        RivalState(
            cash=800,
            inventory=InventoryState(grain=195),
            farm_capacity=10,
            storage_capacity=200,
            route_established=False,
        ),
    ]
    diffs = 0
    mira_storage = 0
    daran_storage = 0
    mira_farm = 0
    daran_farm = 0
    prep = {"build_granary", "buy_grain", "secure_route", "ship_grain"}
    for obs, st in zip(contexts, states, strict=True):
        m = choose_rival_command(MIRA_PROFILE, st, obs)
        d = choose_rival_command(DARAN_PROFILE, st, obs)
        if m.type != d.type:
            diffs += 1
        if m.type in prep:
            mira_storage += 1
        if d.type in prep:
            daran_storage += 1
        if m.type == "expand_farm":
            mira_farm += 1
        if d.type == "expand_farm":
            daran_farm += 1
    assert diffs >= 2, f"expected ≥2 diffs under identical state, got {diffs}"
    assert mira_storage > daran_storage, (
        f"Mira storage/trade {mira_storage} should exceed Daran {daran_storage}"
    )
    assert daran_farm > mira_farm, f"Daran farm {daran_farm} should exceed Mira {mira_farm}"


def test_rival_determinism_same_seed() -> None:
    choices = [PlayerCommand(type="hold") for _ in range(5)]
    g1 = FiveTurnGame(seed="det-rivals-001")
    g2 = FiveTurnGame(seed="det-rivals-001")
    s1 = g1.run(list(choices))
    s2 = g2.run(list(choices))
    assert s1.rival_history == s2.rival_history
    assert g1.rival_history == g2.rival_history
    assert s1.final_rivals == s2.final_rivals
    # Different player choices must lead to different player histories; rivals remain deterministic per seed+turn
    g3 = FiveTurnGame(seed="det-rivals-001")
    diff_choices = [
        PlayerCommand(type="expand_farm"),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
    ]
    s3 = g3.run(diff_choices)
    assert s1.history != s3.history
    # Rival settlement uses resolved prices, so at least one rival wealth differs after divergent player choice
    assert s1.rival_history != s3.rival_history or s1.final_rivals != s3.final_rivals


def test_rival_capital_constraints_via_shared_primitives() -> None:
    # Zero cash forces hold
    poor = RivalState(
        cash=0,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    obs = _obs(home=5000, river=6200)
    m = choose_rival_command(MIRA_PROFILE, poor, obs)
    assert m.type == "hold", f"poor Mira should hold, got {m.type}"
    d = choose_rival_command(DARAN_PROFILE, poor, obs)
    assert d.type == "hold"
    # Execution never negative cash
    game = FiveTurnGame(seed="cap-test")
    s = game.run([PlayerCommand(type="hold") for _ in range(5)])
    for pair in s.rival_history or []:
        for r in pair:
            assert r.after.cash >= 0
            assert r.before.cash >= 0
            assert r.after.inventory.grain >= 0
    # Same costs as actor
    assert EXPAND_FARM_COST == 500
    assert BUILD_GRANARY_COST == 300
    assert ROUTE_ESTABLISH_COST == 400
    # Buy clamping via shared primitive: request 20 with space 5 should cap to 5
    st = RivalState(
        cash=10000,
        inventory=InventoryState(grain=195),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    settlement = SettlementContext(
        world_now="normal",
        home_price_pre=5000,
        river_price_resolved=6200,
        home_price_resolved=5000,
        transport_cost_per_unit=800,
        route_capacity=20,
        reliability_bps=10000,
    )
    res = apply_rival_command(
        MIRA_PROFILE, st, PlayerCommand(type="buy_grain", quantity=20), settlement
    )
    # space is 5, so inventory after buy before harvest is 200, then harvest 100 but capped -> 200, then after settlement 200
    # cash delta should be cost of 5 at 5 per unit =25
    assert res.after.inventory.grain == 200, (
        f"tight buy should cap, got {res.after.inventory.grain}"
    )
    assert res.before.cash - res.after.cash == cost_for_quantity(5, 5000)


def test_rival_no_money_creation_with_price_revaluation() -> None:
    game = FiveTurnGame(seed="money-test")
    game.run([PlayerCommand(type="hold") for _ in range(5)])
    for pair in game.rival_history:
        for r in pair:
            # wealth decomposition mirrors player: cash + qty + price
            assert r.wealth_delta == r.cash_effect + r.quantity_value_effect + r.price_value_effect
    # Explicit hold through price move
    before = RivalState(
        cash=1000,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    settlement = SettlementContext(
        world_now="normal",
        home_price_pre=5000,
        river_price_resolved=5200,
        home_price_resolved=6000,
        transport_cost_per_unit=800,
        route_capacity=20,
        reliability_bps=10000,
    )
    res = apply_rival_command(MIRA_PROFILE, before, PlayerCommand(type="hold"), settlement)
    # Harvest 100, settlement: 20+100=120 capped to 200 ->120, qty effect = value(120,5000)-value(20,5000)=500, price effect = value(120,6000)-value(120,5000)=120, cash 0 => wealth =620
    assert res.quantity_value_effect == value_for(120, 5000) - value_for(20, 5000)
    assert res.price_value_effect == value_for(120, 6000) - value_for(120, 5000)
    assert res.wealth_delta == res.cash_effect + res.quantity_value_effect + res.price_value_effect
    # Ensure no float in wealth accounting
    assert isinstance(res.wealth_delta, int)


def test_rival_behavioral_preparation_vs_concentration() -> None:
    """Warning (next=drought) must boost Mira preparation vs baseline, Daran stays farm-concentrated."""
    identical = RivalState(
        cash=800,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    baseline = _obs(turn=1, world_now="normal", next_known=None, home=5000, river=5200)
    warning = _obs(turn=2, world_now="normal", next_known="drought", home=5000, river=6200)
    mira_baseline_prep = max(
        score_rival_command(
            MIRA_PROFILE,
            identical,
            PlayerCommand(type=t, quantity=10) if t in ("buy_grain",) else PlayerCommand(type=t),  # type: ignore[arg-type]
            baseline,
        )
        for t in ["build_granary", "buy_grain", "secure_route"]
    )
    mira_warning_prep = max(
        score_rival_command(
            MIRA_PROFILE,
            identical,
            PlayerCommand(type=t, quantity=10) if t in ("buy_grain",) else PlayerCommand(type=t),  # type: ignore[arg-type]
            warning,
        )
        for t in ["build_granary", "buy_grain", "secure_route"]
    )
    daran_warning_farm = score_rival_command(
        DARAN_PROFILE, identical, PlayerCommand(type="expand_farm"), warning
    )
    mira_warning_farm = score_rival_command(
        MIRA_PROFILE, identical, PlayerCommand(type="expand_farm"), warning
    )
    assert mira_warning_prep > mira_baseline_prep, (
        f"Mira prep should increase on warning: {mira_baseline_prep} -> {mira_warning_prep}"
    )
    # Mira's prep must exceed her farm under warning (she prepares)
    assert mira_warning_prep > mira_warning_farm, (
        "Mira should value preparation over farm when warning"
    )
    # Daran remains farm-concentrated: his farm > his prep even under warning
    daran_warning_prep = max(
        score_rival_command(
            DARAN_PROFILE,
            identical,
            PlayerCommand(type=t, quantity=10) if t in ("buy_grain",) else PlayerCommand(type=t),  # type: ignore[arg-type]
            warning,
        )
        for t in ["build_granary", "buy_grain", "secure_route"]
    )
    assert daran_warning_farm > daran_warning_prep, (
        "Daran should stay farm-concentrated even on warning"
    )
    # Also check actual chosen commands under warning differ as expected
    m_cmd = choose_rival_command(MIRA_PROFILE, identical, warning)
    d_cmd = choose_rival_command(DARAN_PROFILE, identical, warning)
    assert m_cmd.type in ("build_granary", "buy_grain", "secure_route"), (
        f"Mira under warning should prepare, got {m_cmd.type}"
    )
    assert d_cmd.type == "expand_farm" or d_cmd.type in ("build_granary", "hold"), (
        "Daran under warning should not be more preparatory than Mira"
    )


def test_rival_fingerprint_across_contexts() -> None:
    """Across several controlled contexts Mira flexible > Daran, Daran farm > Mira."""
    contexts = [
        _obs(turn=0, world_now="normal", next_known=None, home=5000, river=5200),
        _obs(turn=2, world_now="normal", next_known="drought", home=5000, river=6200),
        _obs(turn=3, world_now="drought", next_known=None, home=5400, river=6200),
        ObservableContext(
            turn=1,
            world_now="normal",
            next_world_known=None,
            home_price_pre=5000,
            river_price_pre=5200,
            transport_cost_per_unit=800,
            route_capacity=20,
            reliability_bps=10000,
            home_supply=80,
            home_demand=90,
            run_seed="s",
            ruleset_version="1.0",
        ),
        _obs(turn=1, world_now="normal", next_known=None, home=4545, river=5600),
    ]
    # Use same identical state for fingerprint purity (except low-cash / tight already covered in diff test)
    base_state = RivalState(
        cash=800,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    mira_prep = 0
    daran_prep = 0
    mira_farm = 0
    daran_farm = 0
    prep_set = {"build_granary", "buy_grain", "secure_route", "ship_grain"}
    for obs in contexts:
        m = choose_rival_command(MIRA_PROFILE, base_state, obs)
        d = choose_rival_command(DARAN_PROFILE, base_state, obs)
        if m.type in prep_set:
            mira_prep += 1
        if d.type in prep_set:
            daran_prep += 1
        if m.type == "expand_farm":
            mira_farm += 1
        if d.type == "expand_farm":
            daran_farm += 1
    assert mira_prep > daran_prep, f"Mira prep {mira_prep} should exceed Daran {daran_prep}"
    assert daran_farm > mira_farm, f"Daran farm {daran_farm} should exceed Mira {mira_farm}"


def test_headlines_derived_and_visible_after_first_turn() -> None:
    game = FiveTurnGame(seed="headline-test")
    assert len(game.rival_history) == 0
    assert game.rival_headlines_history == ()
    game.run([PlayerCommand(type="hold") for _ in range(5)])
    assert len(game.rival_history) == 5
    assert len(game.rival_headlines_history) == 5
    # Derived property
    for (m_res, d_res), (m_h, d_h) in zip(
        game.rival_history, game.rival_headlines_history, strict=True
    ):
        assert m_res.headline == m_h
        assert d_res.headline == d_h
    # At least one headline per turn after first is non-empty and truthful
    for i, (m_h, d_h) in enumerate(game.rival_headlines_history):
        assert isinstance(m_h, str) and len(m_h) > 10
        assert isinstance(d_h, str) and len(d_h) > 10
        # After T1, at least one is non-empty (they all are)
        if i >= 1:
            assert m_h or d_h
    # Truthfulness: headline must reflect actual after state
    for m_res, d_res in game.rival_history:  # type: ignore[reportGeneralTypeIssues]
        for r in (m_res, d_res):
            if r.command.type == "expand_farm" and "short of cash" not in r.headline:
                assert r.after.farm_capacity == r.before.farm_capacity + EXPAND_FARM_DELTA
                assert r.after.cash == r.before.cash - EXPAND_FARM_COST
            if r.command.type == "build_granary" and "short of cash" not in r.headline:
                assert r.after.storage_capacity == r.before.storage_capacity + BUILD_GRANARY_DELTA
            if r.command.type == "buy_grain" and (
                r.headline.startswith("Mira accumulated")
                or r.headline.startswith("Daran stockpiled")
            ):
                assert (
                    r.after.inventory.grain > r.before.inventory.grain
                    or r.after.cash < r.before.cash
                )
    # Current helper
    assert game.current_rival_headlines() is not None
    # Summary includes rivals
    summary = game.summary()
    assert summary.rival_history is not None
    assert len(summary.rival_history) == 5  # type: ignore[arg-type]
    assert "Mira:" in summary.format() and "Daran:" in summary.format()


def test_rival_execution_same_rules_as_player() -> None:
    """Buy/ship/expand costs and clamping use same actor primitives."""
    # Expand cost parity
    before = RivalState(
        cash=1000,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    settlement = SettlementContext(
        world_now="normal",
        home_price_pre=5000,
        river_price_resolved=6200,
        home_price_resolved=5000,
        transport_cost_per_unit=800,
        route_capacity=20,
        reliability_bps=10000,
    )
    res = apply_rival_command(MIRA_PROFILE, before, PlayerCommand(type="expand_farm"), settlement)
    assert res.after.cash == before.cash - EXPAND_FARM_COST
    assert res.after.farm_capacity == before.farm_capacity + EXPAND_FARM_DELTA
    # Buy clamping parity - space limited
    tight = RivalState(
        cash=10000,
        inventory=InventoryState(grain=195),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    res_buy = apply_rival_command(
        MIRA_PROFILE, tight, PlayerCommand(type="buy_grain", quantity=20), settlement
    )
    # space 5, so only 5 bought
    assert res_buy.after.inventory.grain <= 200
    # Ship clamping parity - capacity 20
    est = RivalState(
        cash=10000,
        inventory=InventoryState(grain=100),
        farm_capacity=10,
        storage_capacity=500,
        route_established=True,
    )
    # Need inventory after harvest: 100 + 100 =200, capacity 20 so ship 30 capped to 20
    res_ship = apply_rival_command(
        MIRA_PROFILE, est, PlayerCommand(type="ship_grain", quantity=30), settlement
    )
    # For est, requested 30 but capacity 20 and inventory ~200 => capped to 20
    assert res_ship.after.inventory.grain == 200 - 20  # 200 pre-ship minus 20 shipped
    assert res_ship.cash_delta == (20 * 10000 // 10000 * 6200 // 1000) - (20 * 800 // 1000)


def test_player_market_isolation() -> None:
    """Rivals must not mutate shared market availability — player supply same as without rivals."""
    from app.engine.turn import resolve_turn as rt

    # Isolated player sequence using raw resolve_turn
    state = FiveTurnGame(seed="iso-test").state
    # Simulate 5 holds via raw engine
    s = state
    for idx in range(5):
        from app.engine.prototype import TURN_SPECS

        spec = TURN_SPECS[idx]
        s = rt(s, PlayerCommand(type="hold"), spec.world, s.to_turn_context()).next_state
    # Now via FiveTurnGame (which also advances rivals)
    g = FiveTurnGame(seed="iso-test")
    g.run([PlayerCommand(type="hold") for _ in range(5)])
    assert g.state.market.supply == s.market.supply
    assert g.state.market.current_price == s.market.current_price
    assert g.state.river_market.current_price == s.river_market.current_price


def test_canonical_run_has_three_diffs() -> None:
    """Canonical hold-5 run must have ≥3 turns where Mira/Daran choose different types."""
    game = FiveTurnGame(seed="demo-seed-001")
    game.run([PlayerCommand(type="hold") for _ in range(5)])
    diffs = sum(1 for m, d in game.rival_history if m.command.type != d.command.type)
    assert diffs >= 3, (
        f"expected ≥3 diff turns in canonical run, got {diffs}: {[(m.command.type, d.command.type) for m, d in game.rival_history]}"
    )


def test_no_float_in_rival_scoring() -> None:
    """Enforce integer discipline — no float in rivals module source."""
    import pathlib

    text = pathlib.Path("backend/app/engine/rivals.py").read_text()
    assert "1e-9" not in text
    filtered = [
        line for line in text.splitlines() if not line.strip().startswith("#") and "float" in line
    ]
    assert not any("float(" in line for line in filtered), f"float usage found: {filtered}"


def test_structured_threat_not_prose_parsing() -> None:
    """Rival scoring must depend on structured next_world_known, not prose signal."""
    # Structural: ObservableContext has no signal field
    assert "signal" not in ObservableContext.model_fields
    assert "next_world_known" in ObservableContext.model_fields
    # Behavioral: same prices/state but different next_world_known must change at least one score
    base_state = RivalState(
        cash=800,
        inventory=InventoryState(grain=20),
        farm_capacity=10,
        storage_capacity=200,
        route_established=False,
    )
    obs_none = _obs(turn=2, world_now="normal", next_known=None, home=5000, river=6200)
    obs_drought = _obs(turn=2, world_now="normal", next_known="drought", home=5000, river=6200)
    # Mira's build_granary score must increase when threat is drought
    s_none = score_rival_command(
        MIRA_PROFILE, base_state, PlayerCommand(type="build_granary"), obs_none
    )
    s_drought = score_rival_command(
        MIRA_PROFILE, base_state, PlayerCommand(type="build_granary"), obs_drought
    )
    assert s_drought > s_none, "structured threat must affect scoring, not prose"


def test_rival_state_has_no_headline() -> None:
    """RivalState must not contain headline field — headline is event, not state."""
    assert "headline" not in RivalState.model_fields
    assert "headline" in RivalTurnResult.model_fields


def test_integer_scoring_exact_tie_rng() -> None:
    """Exact integer tie must be resolved by rng_for, not fuzzy epsilon."""
    poor = RivalState(
        cash=0,
        inventory=InventoryState(grain=0),
        farm_capacity=0,
        storage_capacity=0,
        route_established=False,
    )
    obs = _obs(seed="tie-seed", version="1.0")
    m1 = choose_rival_command(MIRA_PROFILE, poor, obs)
    m2 = choose_rival_command(MIRA_PROFILE, poor, obs)
    assert m1.type == m2.type


def test_partial_buy_insufficient_cash_headline_truthful() -> None:
    """Partial buy (cash limits 10→4) must not say 'could not buy' — headline reflects actual quantity."""
    # Isolate buy by using farm 0 (no harvest) so inventory delta is purely buy
    before = RivalState(
        cash=22,
        inventory=InventoryState(grain=10),
        farm_capacity=0,
        storage_capacity=200,
        route_established=False,
    )
    settlement = SettlementContext(
        world_now="normal",
        home_price_pre=5000,
        river_price_resolved=5200,
        home_price_resolved=5000,
        transport_cost_per_unit=800,
        route_capacity=20,
        reliability_bps=10000,
    )
    res = apply_rival_command(
        MIRA_PROFILE, before, PlayerCommand(type="buy_grain", quantity=10), settlement
    )
    assert res.reason_code == "insufficient_cash"
    # affordable at 5000 with cash 22 => 4 units, cost 20
    assert res.after.cash == 2, f"cash after partial buy should be 2, got {res.after.cash}"
    assert res.after.inventory.grain == 14, (
        f"inventory should be 10+4, got {res.after.inventory.grain}"
    )
    assert res.cash_delta == -20
    assert "could not buy" not in res.headline, (
        f"partial buy headline falsely claims zero: {res.headline}"
    )
    assert "accumulated" in res.headline or "stockpiled" in res.headline
    # Zero-buy counterpart remains false headline
    poor_before = RivalState(
        cash=0,
        inventory=InventoryState(grain=10),
        farm_capacity=0,
        storage_capacity=200,
        route_established=False,
    )
    res_zero = apply_rival_command(
        MIRA_PROFILE, poor_before, PlayerCommand(type="buy_grain", quantity=10), settlement
    )
    assert res_zero.reason_code == "insufficient_cash"
    assert res_zero.after.inventory.grain == 10
    assert "could not buy" in res_zero.headline


def test_partial_ship_insufficient_cash_for_transport_headline_truthful() -> None:
    """Partial ship (transport cash limits 10→7) must not say 'could not ship'."""
    before = RivalState(
        cash=5,
        inventory=InventoryState(grain=50),
        farm_capacity=0,
        storage_capacity=200,
        route_established=True,
    )
    settlement = SettlementContext(
        world_now="normal",
        home_price_pre=5000,
        river_price_resolved=6200,
        home_price_resolved=5000,
        transport_cost_per_unit=800,
        route_capacity=20,
        reliability_bps=10000,
    )
    res = apply_rival_command(
        DARAN_PROFILE, before, PlayerCommand(type="ship_grain", quantity=10), settlement
    )
    assert res.reason_code == "insufficient_cash_for_transport"
    # affordable transport at 800 with cash 5 => 7 units
    assert res.after.inventory.grain == 43, f"50 -7 shipped =43, got {res.after.inventory.grain}"
    # revenue 7*6200//1000=43, cost 7*800//1000=5, trade +38, cash 5+38=43
    assert res.after.cash == 43
    assert "could not ship" not in res.headline, (
        f"partial ship headline falsely claims zero: {res.headline}"
    )
    assert "shipped" in res.headline.lower()
    # Zero-ship counterpart remains — need high transport to force affordable 0
    poor_settlement = SettlementContext(
        world_now="normal",
        home_price_pre=5000,
        river_price_resolved=6200,
        home_price_resolved=5000,
        transport_cost_per_unit=5000,
        route_capacity=20,
        reliability_bps=10000,
    )
    poor_before_ship = RivalState(
        cash=0,
        inventory=InventoryState(grain=50),
        farm_capacity=0,
        storage_capacity=200,
        route_established=True,
    )
    res_zero = apply_rival_command(
        DARAN_PROFILE,
        poor_before_ship,
        PlayerCommand(type="ship_grain", quantity=10),
        poor_settlement,
    )
    assert res_zero.reason_code == "insufficient_cash_for_transport"
    assert res_zero.after.inventory.grain == 50
    assert (
        "could not ship" in res_zero.headline or "short of cash for transport" in res_zero.headline
    )
