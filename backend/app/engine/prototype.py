"""Five-turn headless prototype — Section 6.

Orchestrates exactly five deterministic turns with an authored world/signal arc.
Pure engine: no FastAPI, no DB, no LLM, no rivals (Section 7).

Supply semantics: MarketState.supply is a market-availability signal/index,
drained by demand each turn (turn.py Section 6, not a conserved physical
stock — farm_output also enters player inventory without conservation
implied). Prototype start state is tuned so that surplus is truthfully
weak and drought tightens, making signals truthful.

TURN_SPECS is the only world schedule (hardcoded, not a DSL).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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
from app.engine.turn import resolve_turn

TURN_LIMIT: int = 5


class TurnSpec(BaseModel):
    """One turn's authored world and signal — plain strings, not a DSL."""

    model_config = ConfigDict(frozen=True)

    world: WorldCondition
    signal: str
    title: str


# Truthful signals — each describes actual mechanics, not imaginary deltas.
# T1 demand is high (starting state's demand), T2 surplus is emergent from
# signal + harvest > demand, T3 warning precedes T4 drought, T4 is the
# actual world change, T5 is aftermath.
TURN_SPECS: tuple[TurnSpec, ...] = (
    TurnSpec(
        world="normal",
        title="A Growing Settlement",
        signal="The growing settlement keeps food demand high.",
    ),
    TurnSpec(
        world="normal",
        title="Surplus",
        signal="Repeated harvests have left grain abundant and prices weak.",
    ),
    TurnSpec(
        world="normal",
        title="Warning Signs",
        signal="Dry weather suggests the next harvest may be threatened.",
    ),
    TurnSpec(
        world="drought",
        title="Drought",
        signal="Drought cuts farm output — regional supply tightens.",
    ),
    TurnSpec(
        world="normal",
        title="Aftermath",
        signal="Markets adjust to the drought's aftermath.",
    ),
)


def default_start_state(seed: str = "seed-001", version: str = "1.0") -> GameState:
    """Tuned start state for 5-turn legibility under availability-drained signal.

    Home Valley: supply 100, demand 90 (so signal 100+100-90=110 surplus weak),
    River Town: supply 80, demand 130 (shortage high price), route 800/20/10000.
    Player: cash 1000, grain 20, farm 10, storage 200 (larger to avoid
    immediate cap and let farm expansion be useful).
    """
    return GameState(
        turn=0,
        run_seed=seed,
        ruleset_version=version,
        player=PlayerState(
            cash=1000,
            inventory=InventoryState(grain=20),
            farm_capacity=10,
            storage_capacity=200,
        ),
        market=MarketState(
            supply=100,
            demand=90,
            base_price=5000,
            current_price=5000,
            responsiveness=5000,
            max_movement_bps=2000,
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


class StrategicSummary(BaseModel):
    """Concise end-of-run summary — both human and structured."""

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
        # per-turn highlights
        for i, res in enumerate(self.history):
            spec = TURN_SPECS[i] if i < len(TURN_SPECS) else None
            title = spec.title if spec else f"Turn {i + 1}"
            drivers = (
                ", ".join(d.label for d in res.player_outcome.drivers)
                if res.player_outcome.drivers
                else "no material drivers"
            )
            lines.append(
                f"  T{i + 1} {title}: wealth {res.player_outcome.wealth_delta:+} — {drivers}"
            )
        lines.append("=" * 60)
        return "\n".join(lines)


class FiveTurnGame:
    """In-memory 5-turn game — owns GameState and history, calls resolve_turn."""

    turn_limit: int = TURN_LIMIT

    def __init__(
        self,
        seed: str = "seed-001",
        version: str = "1.0",
        start_state: GameState | None = None,
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

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def history(self) -> tuple[TurnResolution, ...]:
        return tuple(self._history)

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

    def available_commands(self) -> list[str]:
        return ["hold", "expand_farm", "build_granary", "buy_grain", "secure_route", "ship_grain"]

    def submit(self, command: PlayerCommand) -> TurnResolution:
        if self.is_complete:
            raise ValueError("game complete — no more decisions allowed (exactly 5 turns)")
        idx = len(self._history)
        if idx >= len(TURN_SPECS):
            raise ValueError("no world spec for next turn")
        spec = TURN_SPECS[idx]
        # RNG context must equal state's context (validated inside resolve_turn)
        ctx = self._state.to_turn_context()
        res = resolve_turn(self._state, command, spec.world, ctx)
        self._history.append(res)
        self._state = res.next_state
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
        # avoid double count final; use set
        cash_low = min(cash_vals) if cash_vals else self._state.player.cash
        inv_vals = [self._initial_state.player.inventory.grain] + [
            h.next_state.player.inventory.grain for h in self._history
        ]
        peak_inventory = max(inv_vals) if inv_vals else 0
        final_wealth = _wealth(self._state)
        initial_wealth = _wealth(self._initial_state)
        wealth_delta_total = final_wealth - initial_wealth
        # also check sum of wealth deltas equals total (allow for rounding? should be exact via wealth nodes)
        # we keep computed total as ground truth
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
        )
