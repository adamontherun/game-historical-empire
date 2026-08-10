"""Section 8 — Pressure-Driven Event Arc acceptance tests.

Covers AC1-AC5 per Rev 4 plan with mechanism-isolated instrument (F1),
stage/world biconditional (F2), single source causal_source_id (F3),
file location settled (F4), and closeout-ready validation (F5).
No existing test assertions are relaxed.
"""

from __future__ import annotations

import pytest

from app.domain.pressure import PressureState
from app.domain.types import PlayerCommand
from app.engine.pressure import (
    PRESSURE_ARC,
    next_world_known_for_turn,
    pressure_for_turn,
)
from app.engine.prototype import FiveTurnGame


def _hold() -> PlayerCommand:
    return PlayerCommand(type="hold")


def _pressure_stage(world: str) -> PressureState:
    """Helper for direct resolve_turn tests needing a PressureState."""
    # Minimal valid pressure for arbitrary world
    stage = "drought" if world == "drought" else "normal"
    return PressureState(
        pressure_id="test-arc",
        stage=stage,  # type: ignore[arg-type]
        activation_turn=0,
        world=world,  # type: ignore[arg-type]
        signal="test signal",
        title="Test",
    )


# ── AC5 / structural smallness and F2 ──────────────────────────────────


def test_pressure_arc_is_five_stages_in_order() -> None:
    assert len(PRESSURE_ARC) == 5
    stages = [p.stage for p in PRESSURE_ARC]
    assert stages == ["normal", "early_dry", "worsening_dry", "drought", "aftermath"]
    # activation_turn == index
    for idx, p in enumerate(PRESSURE_ARC):
        assert p.activation_turn == idx, f"PRESSURE_ARC[{idx}].activation_turn != {idx}"
    # only drought stage has world drought
    for p in PRESSURE_ARC:
        if p.stage == "drought":
            assert p.world == "drought"
        else:
            assert p.world == "normal"
    # all share same pressure_id
    ids = {p.pressure_id for p in PRESSURE_ARC}
    assert ids == {"northern_drought"}
    # no world_modifiers field (R2/F4)
    assert "world_modifiers" not in PressureState.model_fields


def test_pressure_signals_observational_not_output() -> None:
    assert PRESSURE_ARC[1].signal == "Grain remains abundant, but the rains have begun to fail."
    assert (
        PRESSURE_ARC[2].signal
        == "The dry spell persists. Farmers warn the next harvest is at risk."
    )
    assert PRESSURE_ARC[1].world == "normal"
    assert PRESSURE_ARC[2].world == "normal"
    assert PRESSURE_ARC[1].stage == "early_dry"
    assert PRESSURE_ARC[2].stage == "worsening_dry"
    # All signals must not contain "harvest hints" implying output fell (R4)
    assert "harvest hints" not in PRESSURE_ARC[1].signal.lower()


def test_pressure_state_has_exactly_seven_fields() -> None:
    assert set(PressureState.model_fields.keys()) == {
        "pressure_id",
        "stage",
        "activation_turn",
        "world",
        "signal",
        "title",
        "causal_source_id",
    }


def test_pressure_stage_world_validator() -> None:
    # F2: stage == "drought" <=> world == "drought"
    # early_dry + drought must raise
    with pytest.raises(ValueError):
        PressureState(
            pressure_id="northern_drought",
            stage="early_dry",  # type: ignore[arg-type]
            activation_turn=1,
            world="drought",  # type: ignore[arg-type]
            signal="x",
            title="X",
        )
    with pytest.raises(ValueError):
        PressureState(
            pressure_id="northern_drought",
            stage="worsening_dry",  # type: ignore[arg-type]
            activation_turn=2,
            world="drought",  # type: ignore[arg-type]
            signal="x",
            title="X",
        )
    with pytest.raises(ValueError):
        PressureState(
            pressure_id="northern_drought",
            stage="drought",  # type: ignore[arg-type]
            activation_turn=3,
            world="normal",  # type: ignore[arg-type]
            signal="x",
            title="X",
        )
    # valid combos must not raise
    PressureState(
        pressure_id="northern_drought",
        stage="normal",
        activation_turn=0,
        world="normal",
        signal="x",
        title="X",
    )
    PressureState(
        pressure_id="northern_drought",
        stage="drought",
        activation_turn=3,
        world="drought",
        signal="x",
        title="X",
    )


def test_causal_source_id_single_source() -> None:
    p = PressureState(
        pressure_id="northern_drought",
        stage="worsening_dry",
        activation_turn=2,
        world="normal",
        signal="x",
        title="X",
    )
    assert p.causal_source_id == "pressure:northern_drought:worsening_dry"
    # Explicit override must match formula or raise (F3)
    with pytest.raises(ValueError):
        PressureState(
            pressure_id="northern_drought",
            stage="worsening_dry",
            activation_turn=2,
            world="normal",
            signal="x",
            title="X",
            causal_source_id="pressure:other:id",
        )


# ── F1 / AC1+AC3 mechanism-isolated instrument ───────────────────────────


def test_warning_is_useful_preparation_changes_drought_outcome() -> None:
    """AC1+AC3: warning is useful — same market shock, different exposure.

    Mechanism-isolated (F1): neither history calls expand_farm, so farm_capacity
    stays 10 for both runs and T4 market is provably identical.
    Timing-isolated (Q1): both histories share T1 hold (normal), diverge only at
    T2-T3 warning stages.
    """
    seed = "seed-8-useful"
    prepared = [
        PlayerCommand(type="hold"),
        PlayerCommand(type="build_granary"),
        PlayerCommand(type="buy_grain", quantity=20),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
    ]
    unprepared = [
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
        PlayerCommand(type="hold"),
    ]

    g_prep = FiveTurnGame(seed=seed)
    g_unprep = FiveTurnGame(seed=seed)
    g_prep.run(list(prepared))
    g_unprep.run(list(unprepared))

    prep_t4 = g_prep.history[3]
    unprep_t4 = g_unprep.history[3]

    # Pre-condition affordability: no clamped commands in either run
    for g in (g_prep, g_unprep):
        for res in g.history:
            cmd_node = next(n for n in res.causal_trace.nodes if n.id == "command")
            assert "insufficient" not in cmd_node.reason_code, (
                f"history not affordable: {cmd_node.reason_code} on {cmd_node.label}"
            )
            assert cmd_node.reason_code != "no_route_access"

    # Pre-condition equality (F1): identical T4 market shock
    assert prep_t4.next_state.market.supply == unprep_t4.next_state.market.supply, (
        f"supply must be equal for isolated market: "
        f"{prep_t4.next_state.market.supply} != {unprep_t4.next_state.market.supply}"
    )
    assert prep_t4.next_state.market.current_price == unprep_t4.next_state.market.current_price, (
        f"price must be equal for isolated market: "
        f"{prep_t4.next_state.market.current_price} != {unprep_t4.next_state.market.current_price}"
    )
    # Farm output equality (stronger check)
    prep_farm = next(n for n in prep_t4.causal_trace.nodes if n.id == "farm_output")
    unprep_farm = next(n for n in unprep_t4.causal_trace.nodes if n.id == "farm_output")
    assert prep_farm.after == unprep_farm.after, (
        f"farm_output must be equal: {prep_farm.after} != {unprep_farm.after}"
    )

    # Post-condition (threshold-free, Q5): same shock, different exposure
    prep_pv = next(n for n in prep_t4.causal_trace.nodes if n.id == "price_value_effect")
    unprep_pv = next(n for n in unprep_t4.causal_trace.nodes if n.id == "price_value_effect")
    assert prep_pv.delta != unprep_pv.delta, (
        f"price_value_effect must differ: {prep_pv.delta} vs {unprep_pv.delta}"
    )
    # At least one of wealth or inventory must also differ
    assert (
        prep_t4.player_outcome.wealth_delta != unprep_t4.player_outcome.wealth_delta
        or prep_t4.next_state.player.inventory.grain != unprep_t4.next_state.player.inventory.grain
    ), "wealth_delta or inventory must differ"
    # Concrete evidence (not gating threshold beyond inequality): 130 vs 104, 250 vs 200
    # Keep as documentation value, not a gate — but we assert non-zero delta for sanity
    assert prep_pv.delta is not None and unprep_pv.delta is not None
    assert abs(prep_pv.delta - unprep_pv.delta) > 0  # type: ignore[operator]


def test_drought_still_systemic_via_production_and_supply() -> None:
    """AC2: drought reaches price only through production→supply→price."""
    from app.engine.actor import compute_farm_output

    # Farm output under drought < normal for same capacity
    out_normal, _, _ = compute_farm_output(10, "normal")
    out_drought, _, _ = compute_farm_output(10, "drought")
    assert out_drought < out_normal

    # Trace chain for T4 in a full game
    g = FiveTurnGame(seed="systemic-seed")
    g.run([_hold()] * 5)
    t4 = g.history[3]  # drought turn
    ids = {n.id for n in t4.causal_trace.nodes}
    assert "pressure_stage" in ids
    assert "world" in ids
    # pressure_stage -> world edge
    world_node = next(n for n in t4.causal_trace.nodes if n.id == "world")
    assert "pressure_stage" in world_node.parent_ids
    # farm_output child of world
    farm_node = next(n for n in t4.causal_trace.nodes if n.id == "farm_output")
    assert "world" in farm_node.parent_ids
    # supply child of farm_output
    supply_node = next(n for n in t4.causal_trace.nodes if n.id == "supply")
    assert "farm_output" in supply_node.parent_ids
    # No direct edge pressure_stage -> price
    for pid, cid in t4.causal_trace.edges:
        if pid == "pressure_stage":
            assert cid not in ("price", "home_price", "target_price", "home_target_price"), (
                f"pressure_stage must not directly parent price: edge {pid}->{cid}"
            )
    # pressure_stage node reason_code is causal_source_id (F3)
    p_stage = next(n for n in t4.causal_trace.nodes if n.id == "pressure_stage")
    # Find the pressure for turn 3
    p = pressure_for_turn(3)
    assert p_stage.reason_code == p.causal_source_id
    assert p_stage.reason_code == "pressure:northern_drought:drought"


def test_pressure_chain_determinism_and_inspectability() -> None:
    """AC4: same seed+choices -> identical pressure progression, inspectable."""
    choices = [_hold()] * 5
    g1 = FiveTurnGame(seed="inspect-seed")
    g2 = FiveTurnGame(seed="inspect-seed")
    g1.run(list(choices))
    g2.run(list(choices))
    # Byte-equal state and histories
    assert g1.state == g2.state
    assert g1.history == g2.history
    assert g1.rival_history == g2.rival_history
    # Inspectable via pressure_for_turn and current_pressure
    for idx in range(5):
        assert pressure_for_turn(idx).stage == PRESSURE_ARC[idx].stage
    # current_pressure when not complete
    g = FiveTurnGame(seed="cur-seed")
    assert g.current_pressure is not None
    assert g.current_pressure.stage == "normal"
    g.submit(_hold())  # T1 normal -> now on early_dry
    assert g.current_pressure is not None
    assert g.current_pressure.stage == "early_dry"
    # Run to completion -> current_pressure is None (Q3)
    for _ in range(4):
        g.submit(_hold())
    assert g.is_complete
    assert g.current_pressure is None
    # pressure_for_turn(5) raises
    with pytest.raises(IndexError):
        pressure_for_turn(5)
    # Trace contains pressure_stage node with correct reason_code
    g3 = FiveTurnGame(seed="trace-seed")
    g3.run([_hold()] * 5)
    for idx, res in enumerate(g3.history):
        p_stage = next(n for n in res.causal_trace.nodes if n.id == "pressure_stage")
        expected = pressure_for_turn(idx)
        assert p_stage.reason_code == expected.causal_source_id
        assert p_stage.kind == "pressure"
        assert p_stage.delta is None


def test_no_generic_dsl_smallness_structural() -> None:
    """AC5: small, no DSL — structural, not line-count."""
    assert len(PRESSURE_ARC) == 5
    assert set(PressureState.model_fields.keys()) == {
        "pressure_id",
        "stage",
        "activation_turn",
        "world",
        "signal",
        "title",
        "causal_source_id",
    }
    # No world_modifiers
    assert "world_modifiers" not in PressureState.model_fields
    # File-text scan for forbidden loader substrings in both new modules
    import pathlib

    for rel in ["backend/app/domain/pressure.py", "backend/app/engine/pressure.py"]:
        text = pathlib.Path(rel).read_text()
        lower = text.lower()
        assert "import json" not in lower, f"{rel} must not import json"
        assert "json.load" not in lower, f"{rel} must not use json loader"
        assert "import random" not in lower, f"{rel} must not import random"
        assert "weighted" not in lower, f"{rel} must not contain weighted sampler"
        assert "sampler" not in lower, f"{rel} must not contain sampler"
    # Imports are limited to typing/pydantic/domain (checked via text)
    text = pathlib.Path("backend/app/engine/pressure.py").read_text()
    assert "sqlalchemy" not in text.lower()
    assert "fastapi" not in text.lower()


def test_threat_only_on_worsening_not_early() -> None:
    assert next_world_known_for_turn(1) is None  # early_dry does not threaten
    assert next_world_known_for_turn(2) == "drought"  # worsening does
    assert next_world_known_for_turn(0) is None
    assert next_world_known_for_turn(3) is None
    assert next_world_known_for_turn(4) is None
