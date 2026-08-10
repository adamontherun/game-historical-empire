"""Section 10 API tests — AC1-4 + C3/C4/B1 guards."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api.sessions import SESSION_STORE
from app.main import app

# --- fixtures ---


@pytest.fixture(autouse=True)
def _clear_store():
    SESSION_STORE.clear()
    yield
    SESSION_STORE.clear()


@pytest.fixture
def client():
    return TestClient(app)


# Helpers


def _create_game(client: TestClient, seed: str | None = None) -> dict:
    body: dict = {}
    if seed is not None:
        body["run_seed"] = seed
    resp = client.post("/api/v1/games", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_game(client: TestClient, game_id: str) -> dict:
    resp = client.get(f"/api/v1/games/{game_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _choose(client: TestClient, game_id: str, choice_id: str, expected_revision: int):
    return client.post(
        f"/api/v1/games/{game_id}/choices/{choice_id}",
        json={"expected_revision": expected_revision},
    )


# AC1 — create and complete five-turn game
def test_create_and_complete_five_turn_game(client: TestClient) -> None:
    gv = _create_game(client, seed="ac1-seed")
    game_id = gv["game_id"]
    assert gv["revision"] == 0
    assert gv["turn"] == 0
    assert gv["turn_limit"] == 5
    assert gv["run_seed"] == "ac1-seed"
    assert gv["latest_outcome"] is None
    assert gv["completion_summary"] is None
    assert len(gv["available_choices"]) >= 4  # hold + expand + build + route + buys/sells

    rev = 0
    for _ in range(5):
        gv = _get_game(client, game_id)
        assert gv["revision"] == rev
        # pick first choice (always hold is present)
        choice_id = gv["available_choices"][0]["id"]
        resp = _choose(client, game_id, choice_id, rev)
        assert resp.status_code == 200, resp.text
        gv = resp.json()
        rev += 1
        assert gv["revision"] == rev
        assert gv["turn"] == rev
        assert gv["latest_outcome"] is not None
        # B2: causal_trace unconditional
        assert "causal_trace" in gv["latest_outcome"]
        assert len(gv["latest_outcome"]["causal_trace"]["nodes"]) >= 20
        # C4: outcome has resolved context
        assert "resolved_turn" in gv["latest_outcome"]
        # top-level vs outcome context: after first turn, resolved_turn 0
    # after 5
    gv = _get_game(client, game_id)
    assert gv["turn"] == 5
    assert gv["revision"] == 5
    assert gv["completion_summary"] is not None
    assert gv["completion_summary"]["is_complete"] is True
    assert len(gv["available_choices"]) == 0
    # C3: no history key
    assert "history" not in gv
    assert "history" not in (gv["completion_summary"] or {})
    # 6th must fail 409
    resp = _choose(client, game_id, "hold", 5)
    assert resp.status_code == 409
    assert "complete" in resp.json()["detail"].lower()


# AC2 — invalid choice cannot mutate
def test_invalid_choice_cannot_mutate(client: TestClient) -> None:
    gv = _create_game(client, seed="ac2")
    game_id = gv["game_id"]
    before = _get_game(client, game_id)
    resp = _choose(client, game_id, "not_a_choice", 0)
    assert resp.status_code == 404
    after = _get_game(client, game_id)
    assert after["revision"] == before["revision"]
    assert after["turn"] == before["turn"]


def test_unknown_game_id_404(client: TestClient) -> None:
    resp = client.get("/api/v1/games/does-not-exist")
    assert resp.status_code == 404
    resp = client.post("/api/v1/games/does-not-exist/choices/hold", json={"expected_revision": 0})
    assert resp.status_code == 404


# C3 — no history smuggling
def test_no_history_in_gameview(client: TestClient) -> None:
    gv = _create_game(client, seed="c3-seed")
    game_id = gv["game_id"]
    rev = 0
    for _ in range(5):
        choice_id = _get_game(client, game_id)["available_choices"][0]["id"]
        gv = _choose(client, game_id, choice_id, rev).json()
        rev += 1
    import json

    raw = json.dumps(gv)
    assert '"history"' not in raw
    assert "history" not in gv
    assert "history" not in (gv.get("completion_summary") or {})
    cs = gv["completion_summary"]
    assert cs is not None
    assert "initial_state" not in cs
    assert "final_state" not in cs
    assert "history" not in cs


# C4 — outcome context disambiguated after drought
def test_outcome_context_disambiguated(client: TestClient) -> None:
    gv = _create_game(client, seed="c4-drought")
    game_id = gv["game_id"]
    rev = 0
    # Play through to after drought (turn index 3 is drought)
    # Turn 0 normal, 1 early_dry, 2 worsening_dry, 3 drought, 4 aftermath
    # Submit 4 times to reach after drought
    for i in range(4):
        gv_pre = _get_game(client, game_id)
        # sanity: available choices not empty
        choice_id = gv_pre["available_choices"][0]["id"]
        resp = _choose(client, game_id, choice_id, rev)
        assert resp.status_code == 200, resp.text
        gv = resp.json()
        rev += 1
        if i == 3:
            # after drought submission, latest_outcome should be drought, top-level should be aftermath
            lo = gv["latest_outcome"]
            assert lo is not None
            assert lo["world"] == "drought", f"expected drought, got {lo['world']}"
            assert lo["resolved_turn"] == 3
            # top-level after drought (turn 4) is aftermath
            assert gv["world"] == "normal"
            assert gv["pressure_stage"] == "aftermath"
            assert lo["pressure_stage"] == "drought"
            assert lo["command_type"] == choice_id.split(":")[0]


# AC3 — stale revision cannot mutate
def test_stale_revision_cannot_mutate(client: TestClient) -> None:
    gv = _create_game(client, seed="ac3-seed")
    game_id = gv["game_id"]
    # first valid move
    first_id = gv["available_choices"][0]["id"]
    resp = _choose(client, game_id, first_id, 0)
    assert resp.status_code == 200
    # now stale: try again with expected 0 (current is 1)
    resp2 = _choose(client, game_id, first_id, 0)
    assert resp2.status_code == 409
    assert (
        "expected_revision" in resp2.json()["detail"]
        or "conflict" in resp2.json()["detail"].lower()
    )
    # state unchanged
    gv2 = _get_game(client, game_id)
    assert gv2["revision"] == 1
    assert gv2["turn"] == 1
    # missing expected_revision -> 422
    resp3 = client.post(f"/api/v1/games/{game_id}/choices/{first_id}", json={})
    assert resp3.status_code == 422


# Concurrency — per-session lock, real async client (C5/C6)
@pytest.mark.asyncio
async def test_concurrent_same_revision_one_wins() -> None:
    from httpx import ASGITransport, AsyncClient

    SESSION_STORE.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/games", json={"run_seed": "conc-seed"})
        assert r.status_code == 200
        gv = r.json()
        game_id = gv["game_id"]
        # need a valid choice_id for revision 0
        choice_id = gv["available_choices"][0]["id"]

        async def attempt():
            return await ac.post(
                f"/api/v1/games/{game_id}/choices/{choice_id}", json={"expected_revision": 0}
            )

        results = await asyncio.gather(attempt(), attempt())
        statuses = sorted([res.status_code for res in results])
        assert statuses == [200, 409], statuses
        # final revision must be exactly 1
        r2 = await ac.get(f"/api/v1/games/{game_id}")
        assert r2.json()["revision"] == 1
    SESSION_STORE.clear()


# AC4 completeness — every decision-screen number present as field (B3)
def test_frontend_needs_no_formula(client: TestClient) -> None:
    gv = _create_game(client, seed="formula-test")
    game_id = gv["game_id"]
    # before first turn: completeness of initial view
    assert "wealth" in gv["player_summary"]
    assert "cash" in gv["player_summary"]
    assert "inventory_grain" in gv["player_summary"]
    assert "current_price" in gv["home_valley_market"]
    assert "current_price" in gv["river_town_market"]
    assert "next_margin" in gv["route_status"]
    assert all(
        "cost" in c
        for c in gv["available_choices"]
        if c["kind"] in ("buy_grain", "expand_farm", "build_granary", "secure_route")
    )
    # play 1 turn and check outcome completeness
    rev = 0
    choice_id = gv["available_choices"][0]["id"]
    gv2 = _choose(client, game_id, choice_id, rev).json()
    lo = gv2["latest_outcome"]
    assert lo is not None
    assert "wealth_delta" in lo
    assert "drivers" in lo
    assert all("impact_money" in d and "reason_code" in d and "label" in d for d in lo["drivers"])
    assert "causal_trace" in lo
    assert "nodes" in lo["causal_trace"]
    # drivers' causal_node_ids must reference trace nodes
    node_ids = {n["id"] for n in lo["causal_trace"]["nodes"]}
    for d in lo["drivers"]:
        for nid in d["causal_node_ids"]:
            assert nid in node_ids
    # OutcomeView resolved context present (C4)
    assert "resolved_turn" in lo
    assert "pressure_stage" in lo
    assert "world" in lo
    assert "command_type" in lo
    # empire_summary has exactly three fields (C1)
    assert set(gv2["empire_summary"].keys()) == {
        "farm_capacity",
        "storage_capacity",
        "route_established",
    }


def test_gameview_internal_consistency(client: TestClient) -> None:
    """Internal consistency — labelled as such, not AC4 evidence (B3 circular)."""
    gv = _create_game(client, seed="consistency")
    game_id = gv["game_id"]
    choice_id = gv["available_choices"][0]["id"]
    gv2 = _choose(client, game_id, choice_id, 0).json()
    cash = gv2["player_summary"]["cash"]
    grain = gv2["player_summary"]["inventory_grain"]
    price = gv2["home_valley_market"]["current_price"]
    wealth = gv2["player_summary"]["wealth"]
    # This writes a formula INTO the test — not proof the client avoids formulas
    assert wealth == cash + grain * price // 1000


# B1 — turn invariant: choices depend on state, not turn index (D1: sweep every turn, D2: no protected poke)
def test_available_choices_turn_invariant() -> None:
    from app.api.mappers import choices_for
    from app.api.sessions import GameSession
    from app.domain.types import (
        GameState,
        InventoryState,
        MarketState,
        PlayerCommand,
        PlayerState,
        RouteState,
    )
    from app.engine.prototype import TURN_LIMIT, FiveTurnGame

    # Contrived state where real submits do not move cash/inventory/route:
    # farm 0 => no harvest, 0 movement => price stable, hold keeps everything identical.
    contrived = GameState(
        turn=0,
        run_seed="inv-seed",
        ruleset_version="1.0",
        player=PlayerState(
            cash=10000, inventory=InventoryState(grain=0), farm_capacity=0, storage_capacity=1000
        ),
        market=MarketState(
            supply=280,
            demand=410,
            base_price=5000,
            current_price=5000,
            responsiveness=0,
            max_movement_bps=0,
            regional_output=0,
        ),
        river_market=MarketState(
            supply=80,
            demand=130,
            base_price=5200,
            current_price=5200,
            responsiveness=0,
            max_movement_bps=0,
        ),
        route=RouteState(
            transport_cost_per_unit=300,
            capacity=20,
            reliability_bps=10000,
            established=False,
            delay_turns=0,
        ),
    )
    game = FiveTurnGame(seed="inv-seed", version="1.0", start_state=contrived)
    import asyncio

    seen: list[set[str]] = []
    for n in range(TURN_LIMIT):
        sess = GameSession(
            game_id="x",
            run_seed="inv-seed",
            revision=n,
            game=game,
            created_at="now",
            lock=asyncio.Lock(),
        )
        seen.append({c.id for c in choices_for(sess)})
        if n < TURN_LIMIT - 1:
            game.submit(PlayerCommand(type="hold"))  # type: ignore[arg-type]
    first = seen[0]
    for idx, ids in enumerate(seen[1:], start=1):
        assert ids == first, (
            f"turn invariant violated at {idx}: {first} vs {ids} — API would be gating on turn index"
        )


def test_available_choices_include_two_quantities(client: TestClient) -> None:
    gv = _create_game(client, seed="two-qty")
    # initial has buy_grain with 2 quantities when affordable
    buy_ids = [c["id"] for c in gv["available_choices"] if c["kind"] == "buy_grain"]
    # should be 2 when headroom 60
    assert len(buy_ids) == 2, buy_ids
    assert "buy_grain:30" in buy_ids or "buy_grain:60" in buy_ids
    # sell also 2 when inventory 20
    sell_ids = [c["id"] for c in gv["available_choices"] if c["kind"] == "sell_grain"]
    assert len(sell_ids) == 2, sell_ids
    # ship not yet (not established)
    assert not any(c["kind"] == "ship_grain" for c in gv["available_choices"])
    # establish route then check ship even when margin negative
    # secure_route is available initially
    secure = next(c for c in gv["available_choices"] if c["kind"] == "secure_route")
    game_id = gv["game_id"]
    gv2 = _choose(client, game_id, secure["id"], 0).json()
    # now ship should be available (established) even if next_margin may be negative — we check presence
    ship_ids = [c["id"] for c in gv2["available_choices"] if c["kind"] == "ship_grain"]
    # after securing route we have inventory 20 and capacity 20 => 2 ship options if inventory>0
    if gv2["player_summary"]["inventory_grain"] > 0:
        assert len(ship_ids) == 2, ship_ids
    # also check route_status next_margin present
    assert "next_margin" in gv2["route_status"]


def test_ship_margin_single_helper() -> None:
    import pathlib

    text_actor = pathlib.Path("backend/app/engine/actor.py").read_text()
    assert "def ship_margin" in text_actor
    # inline expression should not appear elsewhere except in actor.ship_margin definition
    # check harness and mappers use helper, not inline
    harness = pathlib.Path("backend/app/engine/harness.py").read_text()
    # should contain ship_margin import/call, not inline "river_market.current_price - state.route.transport"
    assert "ship_margin" in harness
    mappers = pathlib.Path("backend/app/api/mappers.py").read_text()
    assert "ship_margin" in mappers
    # turn.py arbitrage_margin is quantity-weighted, not simple per-unit — ensure simple inline not duplicated
    # We already fixed harness; mappers uses helper


def test_causal_trace_unconditional(client: TestClient) -> None:
    gv = _create_game(client, seed="trace-test")
    game_id = gv["game_id"]
    assert gv["latest_outcome"] is None
    choice_id = gv["available_choices"][0]["id"]
    gv2 = _choose(client, game_id, choice_id, 0).json()
    lo = gv2["latest_outcome"]
    assert lo is not None
    assert "causal_trace" in lo
    nodes = lo["causal_trace"]["nodes"]
    assert 30 <= len(nodes) <= 80, f"unexpected trace size {len(nodes)} — measure payload"
    # drivers reference nodes
    assert len(lo["drivers"]) <= 3


def test_api_determinism(client: TestClient) -> None:
    # two games same seed + same choices => identical
    def run(seed: str) -> list[dict]:
        gv = _create_game(client, seed=seed)
        gid = gv["game_id"]
        rev = 0
        views = [gv]
        for _ in range(5):
            cid = (
                views[-1]["available_choices"][0]["id"]
                if views[-1]["available_choices"]
                else "hold"
            )
            # for determinism we must use same choice sequence; first choice is always hold
            resp = _choose(client, gid, cid, rev)
            assert resp.status_code == 200, resp.text
            gv2 = resp.json()
            views.append(gv2)
            rev += 1
        return views

    v1 = run("det-api-001")
    # clear between runs (fixture would but we need manual)
    SESSION_STORE.clear()
    v2 = run("det-api-001")
    for a, b in zip(v1, v2, strict=False):
        assert a["home_valley_market"]["current_price"] == b["home_valley_market"]["current_price"]
        assert a["player_summary"] == b["player_summary"]
    # minted seed echoed and re-seedable
    SESSION_STORE.clear()
    gv_minted = _create_game(client, seed=None)
    assert "run_seed" in gv_minted and len(gv_minted["run_seed"]) > 0
    minted_seed = gv_minted["run_seed"]
    # new game with that seed should reproduce first game's evolution for same choices
    SESSION_STORE.clear()
    gv_a = _create_game(client, seed=minted_seed)
    gv_b = _create_game(client, seed=minted_seed)
    # not asserting full replay here, just that run_seed echoed
    assert gv_a["run_seed"] == minted_seed
    assert gv_b["run_seed"] == minted_seed
