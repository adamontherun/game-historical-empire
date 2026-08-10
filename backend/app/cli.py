"""Thin CLI for the five-turn headless prototype — Section 6.

Pure I/O around FiveTurnGame; no game logic here.
Supports interactive (input loop) and non-interactive --choices.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure backend is on sys.path when run as script without uv project context
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.types import PlayerCommand
from app.engine.pressure import PRESSURE_ARC
from app.engine.prototype import TURN_SPECS, FiveTurnGame

# Map user tokens to PlayerCommand
_ALIAS = {
    "hold": "hold",
    "h": "hold",
    "1": "hold",
    "expand": "expand_farm",
    "expand_farm": "expand_farm",
    "farm": "expand_farm",
    "2": "expand_farm",
    "granary": "build_granary",
    "build_granary": "build_granary",
    "build": "build_granary",
    "storage": "build_granary",
    "3": "build_granary",
    "buy": "buy_grain",
    "buy_grain": "buy_grain",
    "4": "buy_grain",
    "sell": "sell_grain",
    "sell_grain": "sell_grain",
    "5": "sell_grain",
    "secure": "secure_route",
    "secure_route": "secure_route",
    "route": "secure_route",
    "6": "secure_route",
    "ship": "ship_grain",
    "ship_grain": "ship_grain",
    "7": "ship_grain",
}


def parse_choice(token: str) -> PlayerCommand:
    """Parse a single choice token like 'hold', 'buy 20', 'ship_grain:10', '4'."""
    token = token.strip()
    if not token:
        raise ValueError("empty choice")
    # Support 'buy 20' or 'buy:20' or 'buy_grain:20' or 'buy_grain 20' or '4' or 'hold'
    parts = token.replace(":", " ").split()
    if len(parts) == 1:
        # maybe 'buy_grain:10' already replaced? Actually single part like 'buy_grain:10' -> ['buy_grain','10'] after replace, so this branch is bare type
        typ_token = parts[0].lower()
        qty = None
    elif len(parts) == 2:
        typ_token = parts[0].lower()
        try:
            qty = int(parts[1])
        except ValueError as e:
            raise ValueError(f"invalid quantity in {token!r}") from e
    else:
        raise ValueError(f"invalid choice {token!r} — use like 'hold' or 'buy 20' or 'ship 10'")

    # Normalize alias
    if typ_token not in _ALIAS:
        raise ValueError(
            f"unknown command {typ_token!r} — try hold, expand_farm, build_granary, buy_grain, sell_grain, secure_route, ship_grain"
        )
    cmd_type = _ALIAS[typ_token]
    if cmd_type in ("buy_grain", "sell_grain", "ship_grain"):
        if qty is None:
            qty = 10
        if qty is not None and qty < 0:
            raise ValueError("quantity must be >=0")
        return PlayerCommand(type=cmd_type, quantity=qty)  # type: ignore[arg-type]
    else:
        # quantity ignored for other types
        return PlayerCommand(type=cmd_type)  # type: ignore[arg-type]


def parse_choices_arg(s: str) -> list[PlayerCommand]:
    """Parse comma-separated choices: 'hold,buy 20,hold,ship 10,hold'."""
    if not s:
        return []
    tokens = [t.strip() for t in s.split(",") if t.strip()]
    return [parse_choice(t) for t in tokens]


def format_market_pulse(label: str, supply: int, demand: int, base: int, price: int) -> str:
    return f"{label} supply {supply} demand {demand} base {base} price {price}"


def format_player_state(game: FiveTurnGame) -> str:
    p = game.state.player
    return f"cash {p.cash} grain {p.inventory.grain} farm {p.farm_capacity} storage {p.storage_capacity}"


def format_route_state(game: FiveTurnGame) -> str:
    r = game.state.route
    return f"established={r.established} cost/unit {r.transport_cost_per_unit} capacity {r.capacity} reliability {r.reliability_bps} bps"


def format_rivals(game: FiveTurnGame) -> str:
    mira, daran = game.rivals
    return f"Mira cash {mira.cash} grain {mira.inventory.grain} farm {mira.farm_capacity} storage {mira.storage_capacity} route={mira.route_established} | Daran cash {daran.cash} grain {daran.inventory.grain} farm {daran.farm_capacity} storage {daran.storage_capacity} route={daran.route_established}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Historical Empire — Five-Turn Headless Prototype with Rivals (Section 7)"
    )
    parser.add_argument("--seed", default="seed-001", help="run seed")
    parser.add_argument("--version", default="1.0", help="ruleset version")
    parser.add_argument(
        "--choices",
        default=None,
        help="comma-separated choices for non-interactive run, e.g. 'hold,buy 20,hold,ship 10,hold' or '1,3,1,6:10,1'",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="show full causal trace and domain effects"
    )
    parser.add_argument(
        "--balance",
        action="store_true",
        help="run balance harness (hundreds of games, reports dominance)",
    )
    parser.add_argument(
        "--seeds", type=int, default=200, help="number of seeds for --balance (default 200)"
    )
    parser.add_argument("--seed-prefix", default="harness", help="seed prefix for --balance")
    parser.add_argument("--json-out", default=None, help="write balance JSON to path")
    parser.add_argument("--balance-version", default="1.0", help="ruleset version for --balance")
    args = parser.parse_args(argv)

    # Balance harness path
    if args.balance:
        from app.engine.harness import BatchConfig, format_markdown, run_batch, to_json

        config = BatchConfig(
            seed_prefix=args.seed_prefix, n_seeds=args.seeds, version=args.balance_version
        )
        result = run_batch(config)
        print(format_markdown(result))
        if args.json_out:
            Path(args.json_out).write_text(to_json(result))
            print(f"\nJSON written to {args.json_out}", file=sys.stderr)
        # Exit 2 on any gate breach (reported, now blocking since tuned passes)
        if not (
            result.dominant_gate_pass
            and result.dead_gate_pass
            and result.price_gate_pass
            and result.negativity_gate_pass
            and result.hold_not_top_gate_pass
        ):
            reasons: list[str] = []
            if not result.dominant_gate_pass:
                reasons.append(f"dominant {result.dominant_reason}")
            if not result.dead_gate_pass:
                reasons.append(f"dead {result.dead_reason}")
            if not result.hold_not_top_gate_pass:
                reasons.append(f"hold_not_top {result.hold_not_top_reason}")
            if not result.price_gate_pass:
                reasons.append("price out of bounds")
            if not result.negativity_gate_pass:
                reasons.append("negative state")
            print(f"FAIL: {'; '.join(reasons)}", file=sys.stderr)
            return 2
        return 0

    game = FiveTurnGame(seed=args.seed, version=args.version)

    # Non-interactive path
    if args.choices is not None:
        try:
            choices = parse_choices_arg(args.choices)
        except ValueError as e:
            print(f"error parsing --choices: {e}", file=sys.stderr)
            return 2
        if len(choices) != game.turn_limit:
            print(
                f"error: exactly {game.turn_limit} choices required, got {len(choices)}: {args.choices!r}",
                file=sys.stderr,
            )
            return 2
        # Run headlessly, printing per-turn outcome
        print("=" * 60)
        print(f"Historical Empire — Five-Turn Prototype  seed={args.seed}  version={args.version}")
        print("=" * 60)
        # Show initial
        print(f"\nINITIAL  turn {game.state.turn}  {format_player_state(game)}")
        print(
            f"  HOME  {format_market_pulse('Home', game.state.market.supply, game.state.market.demand, game.state.market.base_price, game.state.market.current_price)}"
        )
        print(
            f"  RIVER {format_market_pulse('River', game.state.river_market.supply, game.state.river_market.demand, game.state.river_market.base_price, game.state.river_market.current_price)}"
        )
        print(f"  ROUTE {format_route_state(game)}")
        for i, cmd in enumerate(choices):
            spec = TURN_SPECS[i]
            pressure = PRESSURE_ARC[i]
            print(f"\n--- TURN {i + 1}/5 — {spec.title} [{pressure.stage}] ---")
            print(f"Signal: {spec.signal}")
            print(
                f"World: {spec.world}  Pressure: {pressure.stage}  Player: {format_player_state(game)}"
            )
            print(
                f"HOME  {format_market_pulse('Home', game.state.market.supply, game.state.market.demand, game.state.market.base_price, game.state.market.current_price)}"
            )
            print(
                f"RIVER {format_market_pulse('River', game.state.river_market.supply, game.state.river_market.demand, game.state.river_market.base_price, game.state.river_market.current_price)}"
            )
            print(f"ROUTE {format_route_state(game)}")
            print(
                "Choices: [1]hold [2]expand_farm [3]build_granary [4]buy 10 [5]secure_route [6]ship 10"
            )
            print(
                f"> Choice: {cmd.type} {f'qty={cmd.quantity}' if cmd.quantity is not None else ''}"
            )
            res = game.submit(cmd)
            # Outcome
            print(
                f"\n  6 MONTHS LATER — wealth {res.player_outcome.wealth_delta:+}  inventory {res.player_outcome.inventory_delta:+}  price {res.player_outcome.price_delta:+}"
            )
            print(
                f"  Home price now {res.next_state.market.current_price}  River now {res.next_state.river_market.current_price}"
            )
            print(f"  Player now {format_player_state(game)}")
            if res.player_outcome.drivers:
                print("  WHY? (top drivers)")
                for j, d in enumerate(res.player_outcome.drivers, 1):
                    print(
                        f"    {j}. {d.label}  [id={d.id} impact={d.impact_money:+} bps={d.impact_bps}]"
                    )
            else:
                print("  WHY? (no material drivers)")
            # Rivals — derived headlines from structured history
            headlines = game.current_rival_headlines()
            if headlines:
                mira_h, daran_h = headlines
                print(f"  MIRA — {mira_h}")
                print(f"  DARAN — {daran_h}")
            if args.verbose:
                print("\n  FULL CAUSAL TRACE")
                for n in res.causal_trace.nodes:
                    print(
                        f"    [{n.id}] {n.label} reason={n.reason_code} before={n.before} after={n.after} delta={n.delta} parents={n.parent_ids}"
                    )
                print("  DOMAIN EFFECTS")
                for e in res.domain_effects:
                    print(
                        f"    {e.metric}: {e.before}->{e.after} ({e.delta:+}) reason={e.reason_code}"
                    )
                # Verbose rival details
                if game.rival_history:
                    mira_r, daran_r = game.rival_history[-1]
                    print("  RIVAL DETAILS")
                    for rr in (mira_r, daran_r):
                        print(
                            f"    {rr.rival_id} cmd={rr.command.type} cash {rr.before.cash}->{rr.after.cash} inv {rr.before.inventory.grain}->{rr.after.inventory.grain} wealth {rr.wealth_delta:+} headline={rr.headline!r}"
                        )
        # Summary
        summary = game.summary()
        print("\n" + summary.format())
        return 0

    # Interactive path
    print("=" * 60)
    print("Historical Empire — Five-Turn Headless Prototype with Rivals")
    print(f"Seed: {args.seed}  Version: {args.version}")
    print("=" * 60)
    print(
        "\nCommands each turn: hold, expand_farm, build_granary, buy 10 (or buy 20), secure_route, ship 10 (or ship 20)"
    )
    print(
        "You make one major action per turn. Type number 1-6 or name like 'hold', 'buy 20', 'ship 10'. Ctrl+D to quit."
    )
    print("Rivals Mira and Daran act each turn — watch their headlines after each reveal.")
    while not game.is_complete:
        spec = game.current_spec()
        assert spec is not None
        pressure = game.current_pressure
        assert pressure is not None
        turn_idx = len(game.history)  # 0-based
        print(f"\n--- TURN {turn_idx + 1}/5 — {spec.title} [{pressure.stage}] ---")
        print(f"Signal: {spec.signal}")
        print(
            f"World will be: {spec.world}  Pressure: {pressure.stage} (resolved after your choice)"
        )
        print(f"Player: {format_player_state(game)}")
        print(
            f"HOME  {format_market_pulse('Home', game.state.market.supply, game.state.market.demand, game.state.market.base_price, game.state.market.current_price)}"
        )
        print(
            f"RIVER {format_market_pulse('River', game.state.river_market.supply, game.state.river_market.demand, game.state.river_market.base_price, game.state.river_market.current_price)}"
        )
        print(f"ROUTE {format_route_state(game)}")
        print("Available actions:")
        print("  [1] Hold (preserve cash)")
        print("  [2] Expand farm  (-500 cash, +10 farm capacity)")
        print("  [3] Build granary (-300 cash, +50 storage)")
        print("  [4] Buy grain 10 (or 'buy 20')")
        print("  [5] Secure river route (-400 cash, establishes trade)")
        print("  [6] Ship grain 10 (requires route, e.g. 'ship 10')")
        # Prompt
        try:
            raw = input("> Choose [1-6 or name]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 130
        if not raw:
            print("Please enter a choice (1-6, hold, buy 20, etc.)")
            continue
        try:
            cmd = parse_choice(raw)
        except ValueError as e:
            print(f"Invalid: {e}")
            continue
        try:
            res = game.submit(cmd)
        except ValueError as e:
            print(f"Error: {e}")
            continue
        print(
            f"\n  6 MONTHS LATER — wealth {res.player_outcome.wealth_delta:+}  inventory {res.player_outcome.inventory_delta:+}  price {res.player_outcome.price_delta:+}"
        )
        print(
            f"  Home price now {res.next_state.market.current_price}  River now {res.next_state.river_market.current_price}"
        )
        print(f"  Player now {format_player_state(game)}")
        # Rivals
        headlines = game.current_rival_headlines()
        if headlines:
            mira_h, daran_h = headlines
            print(f"  MIRA — {mira_h}")
            print(f"  DARAN — {daran_h}")
        if res.player_outcome.drivers:
            print("  WHY? (top drivers)")
            for j, d in enumerate(res.player_outcome.drivers, 1):
                print(f"    {j}. {d.label}")
        else:
            print("  WHY? (no material drivers)")
        if args.verbose:
            print("\n  FULL CAUSAL TRACE")
            for n in res.causal_trace.nodes:
                print(f"    [{n.id}] {n.label} reason={n.reason_code}")
            if game.rival_history:
                mira_r, daran_r = game.rival_history[-1]
                print(f"  RIVAL: Mira {mira_r.headline}")
                print(f"  RIVAL: Daran {daran_r.headline}")

    summary = game.summary()
    print("\n" + summary.format())
    print("\nGame complete — 5 turns. Thanks for playing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
