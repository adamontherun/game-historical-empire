"""CLI demo for Section 4 — prints before state, command, world, causal chain, after state.

Supports concise (default) and verbose (--verbose/--debug) modes.
Concise shows WHY? with ≤3 story drivers (exact wealth-bps ranked).
Verbose adds full causal trace and domain effects.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `backend` is on sys.path when run as script without PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.domain.types import GameState, InventoryState, MarketState, PlayerCommand, PlayerState
from app.engine.turn import TURN_ORDER, resolve_turn


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
        f"player cash: {state.player.cash}  grain: {state.player.inventory.grain}  farm: {state.player.farm_capacity}  storage: {state.player.storage_capacity}"
    )
    print(
        f"market supply: {state.market.supply}  demand: {state.market.demand}  base: {state.market.base_price}  price: {state.market.current_price}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Section 4 causal explanation demo")
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
    parser.add_argument(
        "--verbose",
        "--debug",
        action="store_true",
        dest="verbose",
        help="show full causal trace and domain effects",
    )
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
    print("Historical Empire — Section 4 Causal Explanation Demo")
    print(f"TURN_ORDER: {TURN_ORDER}")
    print("=" * 60)
    _print_state("BEFORE STATE", state)
    print(f"\nCOMMAND: {cmd.type} {f'qty={cmd.quantity}' if cmd.quantity is not None else ''}")
    print(f"WORLD CONDITION: {world}")

    res = resolve_turn(state, cmd, world, state.to_turn_context())

    # Concise outcome — always shown
    print("\n--- PLAYER OUTCOME (concise) ---")
    print(f"wealth_delta: {res.player_outcome.wealth_delta:+}  (cash + inventory value)")
    print(f"inventory_delta: {res.player_outcome.inventory_delta:+}")
    print(f"price_delta: {res.player_outcome.price_delta:+}")
    # Show wealth decomposition sum check
    print("\nWHY? (top story drivers, ranked by exact wealth-bps)")
    if not res.player_outcome.drivers:
        print("(no material drivers — all wealth effects zero)")
    else:
        for i, d in enumerate(res.player_outcome.drivers, 1):
            print(
                f"{i}. {d.label}  [id={d.id} impact={d.impact_money:+} bps={d.impact_bps} "
                f"nodes={d.causal_node_ids} reason={d.reason_code}]"
            )
        # Verify exact sum
        total = sum(d.impact_money for d in res.player_outcome.drivers)
        # Note: drivers are ≤3 of possibly >3 effects; but for this
        # exact partition, sum of all drivers should be ≤ wealth_delta
        # Actually with exact partition (cash+quantity+price), sum of
        # drivers == wealth_delta when all 3 present
        # When filtered zero, sum may be < wealth_delta but we show check
        print(f"  drivers sum: {total:+}  wealth_delta: {res.player_outcome.wealth_delta:+}")

    print("\n--- AFTER STATE (next_state) ---")
    _print_state("AFTER STATE", res.next_state)

    if args.verbose:
        print("\n--- FULL CAUSAL TRACE (debug) ---")
        for node in res.causal_trace.nodes:
            parents = f"  parents={node.parent_ids}" if node.parent_ids else ""
            delta_str = f" delta={node.delta}" if node.delta is not None else ""
            before_after = ""
            if node.before is not None or node.after is not None:
                before_after = f"  before={node.before} after={node.after}"
            print(
                f"[{node.id}] {node.label}  reason={node.reason_code}{before_after}{delta_str}{parents}"
            )

        print("\n--- DOMAIN EFFECTS (debug) ---")
        for eff in res.domain_effects:
            print(
                f"{eff.metric}: {eff.before} -> {eff.after} ({eff.delta:+}) "
                f"reason={eff.reason_code}"
            )

        print("\n--- DRIVERS (structured) ---")
        for d in res.player_outcome.drivers:
            print(
                f"driver {d.id}: kind={d.kind} impact={d.impact_money:+} bps={d.impact_bps} "
                f"causal_node_ids={d.causal_node_ids}"
            )

        print("\n--- EDGES (derived) ---")
        print(f"edges: {res.causal_trace.edges}")

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
    print(
        f"  wealth_delta {res2.player_outcome.wealth_delta:+} "
        f"drivers: {res2.player_outcome.top_drivers}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
