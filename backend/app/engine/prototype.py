"""Five-turn headless prototype — Section 8 pressure-driven arc.

Orchestrates exactly five deterministic turns with an authored pressure arc
and session-owned rivals Mira/Daran (pure, no DB, no LLM, isolated supply).

Supply semantics: MarketState.supply is a market-availability signal/index,
drained by demand each turn (turn.py Section 6). Rivals do not mutate the
shared availability signal in Section 7 (isolation).

PRESSURE_ARC (engine/pressure.py) is now the single source; TURN_SPECS is
derived for backward compatibility. Structured threat `next_world_known`
is derived from pressure stage (worsening_dry → drought), not prose.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.domain.pressure import PressureState
from app.domain.trace import TurnResolution
from app.domain.types import (
    GameState,
    InventoryState,
    MarketState,
    PlayerCommand,
    PlayerState,
    RouteState,
    WorldCondition,
)
from app.engine.pressure import (
    PRESSURE_ARC,
    next_world_known_for_turn,
    pressure_for_turn,
)
from app.engine.rivals import (
    DARAN_PROFILE,
    DARAN_START_STATE,
    MIRA_PROFILE,
    MIRA_START_STATE,
    ObservableContext,
    RivalState,
    RivalTurnResult,
    SettlementContext,
    apply_rival_command,
    choose_rival_command,
)
from app.engine.turn import resolve_turn

TURN_LIMIT: int = 5


class TurnSpec(BaseModel):
    """One turn's authored world and signal — plain strings, not a DSL."""

    model_config = ConfigDict(frozen=True)

    world: WorldCondition
    signal: str
    title: str


# PRESSURE_ARC is the single source (Section 8); TURN_SPECS derived for
# backward compatibility (existing tests import TURN_SPECS).
TURN_SPECS: tuple[TurnSpec, ...] = tuple(
    TurnSpec(world=p.world, signal=p.signal, title=p.title) for p in PRESSURE_ARC
)


def default_start_state(seed: str = "seed-001", version: str = "1.0") -> GameState:
    """Tuned start state — Section 9 regional_output economy (final).

    Home Valley: regional_output 360 + farm 10*10=100 => total 460, player 21.7%
    (within 15-25%). Demand 400 gives signal_next≈signal+60 surplus in normal
    (mild softening), drought cuts regional to 216 + farm 60 = 276
    => signal_next≈signal-124 (shortage, price spike). Supply 280.
    Responsiveness 4000 (down from 5000) keeps price within bounds while
    farm expansion remains viable. River unchanged. Player: cash 1000 grain 20
    farm 10 storage 400 (was 200, cap was binding). Tuned empirically via
    harness — balance table shows no dominant/dead (median ratio <1.6).
    Rival diffs ≥3 restored (Mira ≠ Daran).
    """
    return GameState(
        turn=0,
        run_seed=seed,
        ruleset_version=version,
        player=PlayerState(
            cash=1000,
            inventory=InventoryState(grain=20),
            farm_capacity=10,
            storage_capacity=400,
        ),
        market=MarketState(
            supply=280,
            demand=400,
            base_price=5000,
            current_price=5000,
            responsiveness=4000,
            max_movement_bps=2000,
            regional_output=360,
        ),
        river_market=MarketState(
            supply=80,
            demand=130,
            base_price=5200,
            current_price=5200,
            responsiveness=5000,
            max_movement_bps=2000,
        ),
        route=RouteState(
            transport_cost_per_unit=800,
            capacity=20,
            reliability_bps=10000,
            established=False,
            delay_turns=0,
            event_exposure="river_risk",
        ),
    )


def _wealth(state: GameState) -> int:
    """Wealth = cash + inventory value at Home price (milli)."""
    return state.player.cash + (state.player.inventory.grain * state.market.current_price // 1000)


# Backward compat shim: pre-Section 8 code called _next_world_known_for_turn
def _next_world_known_for_turn(idx: int) -> WorldCondition | None:  # noqa: D103
    return next_world_known_for_turn(idx)


class StrategicSummary(BaseModel):
    """Concise end-of-run summary — both human and structured (now with rivals)."""

    model_config = ConfigDict(frozen=True)

    initial_state: GameState
    final_state: GameState
    history: tuple[TurnResolution, ...]
    final_wealth: int
    initial_wealth: int
    wealth_delta_total: int
    cash_low: int
    peak_inventory: int
    is_complete: bool
    # Section 7 — optional to keep backward compat with tests that construct manually
    final_rivals: tuple[RivalState, RivalState] | None = None
    rival_history: tuple[tuple[RivalTurnResult, RivalTurnResult], ...] | None = None

    def format(self) -> str:
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("STRATEGIC SUMMARY — 5 turns")
        lines.append(
            f"  initial wealth: {self.initial_wealth}  final wealth: {self.final_wealth}  delta: {self.wealth_delta_total:+}"
        )
        lines.append(
            f"  final cash: {self.final_state.player.cash}  cash low: {self.cash_low}  peak grain: {self.peak_inventory}"
        )
        lines.append(
            f"  final grain: {self.final_state.player.inventory.grain}  farm: {self.final_state.player.farm_capacity}  storage: {self.final_state.player.storage_capacity}"
        )
        lines.append(
            f"  home price: {self.initial_state.market.current_price} → {self.final_state.market.current_price}"
        )
        lines.append(
            f"  river price: {self.initial_state.river_market.current_price} → {self.final_state.river_market.current_price}"
        )
        # per-turn highlights — include pressure stage per G2
        for i, res in enumerate(self.history):
            spec = TURN_SPECS[i] if i < len(TURN_SPECS) else None
            title = spec.title if spec else f"Turn {i + 1}"
            pressure = PRESSURE_ARC[i] if i < len(PRESSURE_ARC) else None
            stage = f" [{pressure.stage}]" if pressure else ""
            drivers = (
                ", ".join(d.label for d in res.player_outcome.drivers)
                if res.player_outcome.drivers
                else "no material drivers"
            )
            lines.append(
                f"  T{i + 1} {title}{stage}: wealth {res.player_outcome.wealth_delta:+} — {drivers}"
            )
        # Rival per-turn headlines (derived)
        if self.rival_history is not None:
            for i, pair in enumerate(self.rival_history):
                mira, daran = pair
                lines.append(f"  T{i + 1} Rivals: Mira: {mira.headline} | Daran: {daran.headline}")
            if self.final_rivals is not None:
                mr, dr = self.final_rivals
                lines.append(
                    f"  final rivals: Mira cash {mr.cash} grain {mr.inventory.grain} farm {mr.farm_capacity} storage {mr.storage_capacity} | Daran cash {dr.cash} grain {dr.inventory.grain} farm {dr.farm_capacity} storage {dr.storage_capacity}"
                )
        lines.append("=" * 60)
        return "\n".join(lines)


class FiveTurnGame:
    """In-memory 5-turn game — owns GameState, history, and session rivals.

    Rivals are session-owned (not in GameState) — they do not mutate shared
    availability signal in Section 7 (isolation). Timing is two-phase:
    rivals choose from pre-turn observable info, player market resolves, then
    rivals settle at pre-buy price + resolved River/Home prices.
    """

    turn_limit: int = TURN_LIMIT

    def __init__(
        self,
        seed: str = "seed-001",
        version: str = "1.0",
        start_state: GameState | None = None,
        mira_state: RivalState | None = None,
        daran_state: RivalState | None = None,
    ) -> None:
        self._seed = seed
        self._version = version
        self._initial_state = (
            start_state if start_state is not None else default_start_state(seed, version)
        )
        if self._initial_state.turn != 0:
            raise ValueError(
                f"start_state.turn must be 0 for Section 6 (got {self._initial_state.turn}) — resume semantics belong to later sections, Section 6 requires exactly five decisions from turn 0"
            )
        # ensure seed/version match state
        if self._initial_state.run_seed != seed or self._initial_state.ruleset_version != version:
            # if caller passed start_state with different seed/version, respect state's values
            self._seed = self._initial_state.run_seed
            self._version = self._initial_state.ruleset_version
        self._state: GameState = self._initial_state
        self._history: list[TurnResolution] = []
        # Session-owned rivals — independent economic states
        self._rivals: dict[str, RivalState] = {
            "mira": mira_state if mira_state is not None else MIRA_START_STATE,
            "daran": daran_state if daran_state is not None else DARAN_START_STATE,
        }
        self._rival_history: list[tuple[RivalTurnResult, RivalTurnResult]] = []

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def history(self) -> tuple[TurnResolution, ...]:
        return tuple(self._history)

    @property
    def rivals(self) -> tuple[RivalState, RivalState]:
        return (self._rivals["mira"], self._rivals["daran"])

    @property
    def rival_history(
        self,
    ) -> tuple[tuple[RivalTurnResult, RivalTurnResult], ...]:
        return tuple(self._rival_history)

    @property
    def rival_headlines_history(self) -> tuple[tuple[str, str], ...]:
        """Derived headlines per turn for UI convenience."""
        return tuple((m.headline, d.headline) for m, d in self._rival_history)

    def current_rival_headlines(self) -> tuple[str, str] | None:
        if not self._rival_history:
            return None
        m, d = self._rival_history[-1]
        return (m.headline, d.headline)

    @property
    def is_complete(self) -> bool:
        return len(self._history) >= self.turn_limit or self._state.turn >= self.turn_limit

    @property
    def current_turn(self) -> int:
        return self._state.turn

    def current_spec(self) -> TurnSpec | None:
        if self.is_complete:
            return None
        idx = len(self._history)
        if 0 <= idx < len(TURN_SPECS):
            return TURN_SPECS[idx]
        return None

    def current_signal(self) -> str:
        spec = self.current_spec()
        return spec.signal if spec else ""

    def current_title(self) -> str:
        spec = self.current_spec()
        return spec.title if spec else "Complete"

    @property
    def current_pressure(self) -> PressureState | None:
        """Current pressure stage, None when game is complete (Q3)."""
        if self.is_complete:
            return None
        idx = len(self._history)
        if 0 <= idx < len(PRESSURE_ARC):
            return pressure_for_turn(idx)
        return None

    def available_commands(self) -> list[str]:
        return [
            "hold",
            "expand_farm",
            "build_granary",
            "buy_grain",
            "sell_grain",
            "secure_route",
            "ship_grain",
        ]

    def _observable_for(self, idx: int) -> ObservableContext:
        """Build pre-turn observable context for rival choice (structured, not prose)."""
        pressure = pressure_for_turn(idx)
        return ObservableContext(
            turn=idx,
            world_now=pressure.world,
            next_world_known=next_world_known_for_turn(idx),
            home_price_pre=self._state.market.current_price,
            river_price_pre=self._state.river_market.current_price,
            transport_cost_per_unit=self._state.route.transport_cost_per_unit,
            route_capacity=self._state.route.capacity,
            reliability_bps=self._state.route.reliability_bps,
            home_supply=self._state.market.supply,
            home_demand=self._state.market.demand,
            run_seed=self._seed,
            ruleset_version=self._version,
        )

    def submit(self, command: PlayerCommand) -> TurnResolution:
        if self.is_complete:
            raise ValueError("game complete — no more decisions allowed (exactly 5 turns)")
        idx = len(self._history)
        if idx >= len(TURN_SPECS):
            raise ValueError("no world spec for next turn")
        pressure = pressure_for_turn(idx)

        # 1. Rivals choose from pre-turn observable info (before player resolution)
        obs = self._observable_for(idx)
        mira_before = self._rivals["mira"]
        daran_before = self._rivals["daran"]
        mira_choice = choose_rival_command(MIRA_PROFILE, mira_before, obs)
        daran_choice = choose_rival_command(DARAN_PROFILE, daran_before, obs)

        # 2. Resolve player/world market turn (authoritative)
        ctx = self._state.to_turn_context()
        res = resolve_turn(self._state, command, pressure, ctx)
        self._history.append(res)
        self._state = res.next_state

        # 3. Rivals settle using correct timing: buy at pre, ship at resolved River, valuation at resolved Home
        settlement = SettlementContext(
            world_now=pressure.world,
            home_price_pre=obs.home_price_pre,
            river_price_resolved=res.next_state.river_market.current_price,
            home_price_resolved=res.next_state.market.current_price,
            transport_cost_per_unit=obs.transport_cost_per_unit,
            route_capacity=obs.route_capacity,
            reliability_bps=obs.reliability_bps,
        )
        mira_result = apply_rival_command(MIRA_PROFILE, mira_before, mira_choice, settlement)
        daran_result = apply_rival_command(DARAN_PROFILE, daran_before, daran_choice, settlement)
        self._rivals["mira"] = mira_result.after
        self._rivals["daran"] = daran_result.after
        self._rival_history.append((mira_result, daran_result))
        return res

    def run(self, choices: list[PlayerCommand]) -> StrategicSummary:
        if len(choices) != self.turn_limit:
            raise ValueError(f"exactly {self.turn_limit} choices required, got {len(choices)}")
        for cmd in choices:
            self.submit(cmd)
        return self.summary()

    def summary(self) -> StrategicSummary:
        # cash low and peak inventory across history + initial
        cash_vals = (
            [self._initial_state.player.cash]
            + [h.next_state.player.cash for h in self._history]
            + [self._state.player.cash]
        )
        cash_low = min(cash_vals) if cash_vals else self._state.player.cash
        inv_vals = [self._initial_state.player.inventory.grain] + [
            h.next_state.player.inventory.grain for h in self._history
        ]
        peak_inventory = max(inv_vals) if inv_vals else 0
        final_wealth = _wealth(self._state)
        initial_wealth = _wealth(self._initial_state)
        wealth_delta_total = final_wealth - initial_wealth
        final_rivals = (self._rivals["mira"], self._rivals["daran"])
        rival_hist = tuple(self._rival_history)
        return StrategicSummary(
            initial_state=self._initial_state,
            final_state=self._state,
            history=tuple(self._history),
            final_wealth=final_wealth,
            initial_wealth=initial_wealth,
            wealth_delta_total=wealth_delta_total,
            cash_low=cash_low,
            peak_inventory=peak_inventory,
            is_complete=self.is_complete,
            final_rivals=final_rivals,
            rival_history=rival_hist,
        )
