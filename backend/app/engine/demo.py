"""CLI demo for Section 3 — prints before state, command, world, causal chain, after state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `backend` is on sys.path when run as script without PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.domain.types import GameState, InventoryState, MarketState, PlayerCommand, PlayerState
from app.engine.turn import resolve_turn


def _sample_state() -> GameState:
    return GameState(
        turn=0,
        run_seed="demo-seed-001",
        ruleset_version="1.0",
        player=PlayerState(
            cash=1000,
            inventory=InventoryState(grain=20),
            farm_capacity=10,
            storage_capacity=100,
        ),
        market=MarketState(
            supply=100,
            demand=120,
            base_price=5000,
            current_price=5000,
            responsiveness=5000,
            max_movement_bps=2000,
        ),
    )


def _print_state(label: str, state: GameState) -> None:
    print(f"--- {label} ---")
    print(f"turn: {state.turn}  seed: {state.run_seed}  ruleset: {state.ruleset_version}")
    print(
        f"player cash: {state.player.cash}  grain: {state.player.inventory.grain}  farm: {state.player.farm_capacity}  storage: {state.player.storage_capacity}"  # noqa: E501
    )
    print(
        f"market supply: {state.market.supply}  demand: {state.market.demand}  base: {state.market.base_price}  price: {state.market.current_price}"  # noqa: E501
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Section 3 grain market demo")
    parser.add_argument("--seed", default="demo-seed-001", help="run seed")
    parser.add_argument(
        "--world", choices=["normal", "drought"], default="drought", help="world condition"
    )
    parser.add_argument(
        "--command",
        choices=["expand_farm", "build_granary", "buy_grain", "hold"],
        default="hold",
        help="player command",
    )
    parser.add_argument("--qty", type=int, default=20, help="quantity for buy_grain")
    args = parser.parse_args()

    state = _sample_state()
    # Override seed if provided
    state = GameState(
        turn=state.turn,
        run_seed=args.seed,
        ruleset_version=state.ruleset_version,
        player=state.player,
        market=state.market,
    )

    if args.command == "buy_grain":
        cmd = PlayerCommand(type="buy_grain", quantity=args.qty)
    else:
        cmd = PlayerCommand(type=args.command)  # type: ignore[arg-type]

    world = args.world  # type: ignore[assignment]

    print("=" * 60)
    print("Historical Empire — Section 3 Grain Market Kernel Demo")
    print("TURN_ORDER: command -> production -> supply -> price -> settlement")
    print("=" * 60)
    _print_state("BEFORE STATE", state)
    print(f"\nCOMMAND: {cmd.type} {f'qty={cmd.quantity}' if cmd.quantity is not None else ''}")
    print(f"WORLD CONDITION: {world}")

    res = resolve_turn(state, cmd, world, state.to_turn_context())

    print("\n--- CAUSAL CHAIN ---")
    for node in res.causal_trace.nodes:
        parents = f"  parents={node.parent_ids}" if node.parent_ids else ""
        delta_str = f" delta={node.delta}" if node.delta is not None else ""
        before_after = ""
        if node.before is not None or node.after is not None:
            before_after = f"  before={node.before} after={node.after}"
        print(
            f"[{node.id}] {node.label}  reason={node.reason_code}{before_after}{delta_str}{parents}"
        )

    print("\n--- DOMAIN EFFECTS ---")
    for eff in res.domain_effects:
        print(f"{eff.metric}: {eff.before} -> {eff.after} ({eff.delta:+}) reason={eff.reason_code}")

    print("\n--- PLAYER OUTCOME ---")
    print(f"wealth_delta: {res.player_outcome.wealth_delta:+}")
    print(f"inventory_delta: {res.player_outcome.inventory_delta:+}")
    print(f"price_delta: {res.player_outcome.price_delta:+}")
    print(f"top_drivers: {res.player_outcome.top_drivers}")

    _print_state("AFTER STATE (next_state)", res.next_state)
    print("\nDone.")

    # Also show contrasting world for same command to illustrate opportunity cost
    other_world = "normal" if world == "drought" else "drought"
    res2 = resolve_turn(state, cmd, other_world, state.to_turn_context())  # type: ignore[arg-type]
    print("\n" + "=" * 60)
    print(f"CONTRAST: same command '{cmd.type}' under world '{other_world}'")
    print(
        f"  price {state.market.current_price} -> {res2.next_state.market.current_price}"
        f" (delta {res2.player_outcome.price_delta:+})"
    )
    print(f"  supply {state.market.supply} -> {res2.next_state.market.supply}")
    print(f"  inventory {state.player.inventory.grain} -> {res2.next_state.player.inventory.grain}")
    print("=" * 60)


if __name__ == "__main__":
    main()
