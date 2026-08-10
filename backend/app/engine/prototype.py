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
from app.engine.actor import value_for
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
    """Tuned start state — Section 9 retuned for binding constraints (storage scarcity, route viability).

    Home Valley: regional_output 360 + farm 5*10=50 => total 410, player 12.2%
    (was 21.7% with farm 10, now lower so free baseline does not saturate storage).
    Demand 410 vs supply 280 creates persistent tightness (baseline price 5928, not 5000)
    so drought 280→116 gives 7113 spike within 20% cap. Demand 410 gives signal_next≈signal+0
    stable in normal (mild), drought cuts regional to 216 + farm 30 = 246 => signal_next≈signal-164 shortage.
    Supply 280. Responsiveness 4000 keeps price within [2000,9000]. River unchanged.
    Player: cash 1000 grain 20 farm 5 storage 130 (was 400 — makes granary load-bearing;
    idle accumulates 270 over 5 turns so 400 never binds, 130 does; 130 chosen as
    widest-margin point in sweep 100-150 where hold rank ≥3 with 8.6% margin,
    ratio 1.02, price 3876-8535; 100 gave rank2, 115-120 <5%, 125 6.6%, 135 9.1% but
    130 is rounder and >5% threshold). Route: capacity 20 (reverted from 60 — R3:
    route repays at 20 with transport 300, +174 on 400 cost; 60 gave +280 but
    strains price-taking approximation), transport 300 (was 800 — leaves real margin
    after toll while preserving margin-negative at drought peak). Tuned with
    competent policies to clear hold rank ≥3 with >5% margin. Price-taking boundary:
    player sales/shipments are price-taking; endogenous price impact deferred to
    Section 14.
    """
    return GameState(
        turn=0,
        run_seed=seed,
        ruleset_version=version,
        player=PlayerState(
            cash=1000,
            inventory=InventoryState(grain=20),
            farm_capacity=5,
            storage_capacity=130,
        ),
        market=MarketState(
            supply=280,
            demand=410,
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
            transport_cost_per_unit=300,
            capacity=20,
            reliability_bps=10000,
            established=False,
            delay_turns=0,
            event_exposure="river_risk",
        ),
    )


def _wealth(state: GameState) -> int:
    """Wealth = cash + grain*home_price + finished*finished_price (milli)."""
    from app.engine.actor import FINISHED_GOODS_PRICE, FINISHED_GOODS_PRICE_RIVER_EXTRA

    finished_price = FINISHED_GOODS_PRICE + (
        FINISHED_GOODS_PRICE_RIVER_EXTRA if "river_contracts" in state.legacies else 0
    )
    return (
        state.player.cash
        + value_for(state.player.inventory.grain, state.market.current_price)
        + value_for(state.player.inventory.finished_goods, finished_price)
    )


# Section 13 — epilogue constants
EPILOGUE_TURNS: int = 3
EIGHT_TURN_LIMIT: int = 5 + EPILOGUE_TURNS  # 8


def derive_legacies(summary: StrategicSummary) -> tuple[str, ...]:
    """Derive legacies deterministically from final agricultural state.

    Three legacies — crisis_reputation dropped because it was a constant (40/40 on all
    deterministic policies at any threshold that keeps ~25-40% overall; inventory_at_drought
    is fixed per policy: production 130, storage 180, trade 110, cash 130 — so any threshold
    either keeps 4/4 or 3/4 or 1/4, never a discriminating 2/4, and cash_low >=300 is always true).
    Three real legacies beat four where one is a baseline.
    - granary_expertise: final_storage >=180 (inert in new regime — deliberately not craft bonus)
    - river_contracts: route_established (grants +2 labour — the disruption)
    - land_network: final_farm >=15 (weak +15 grain vs labour×10)
    """
    leg: list[str] = []
    fs = summary.final_state
    if fs.player.storage_capacity >= 180:
        leg.append("granary_expertise")
    if fs.route.established:
        leg.append("river_contracts")
    if fs.player.farm_capacity >= 15:
        leg.append("land_network")
    return tuple(leg)


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


class EightTurnGame:
    """Eight-turn game — 5 agriculture + 3 epilogue (Section 13).

    Orchestrates 5-turn agriculture via FiveTurnGame, then derives legacies deterministically
    and continues 3 epilogue turns with demand shift 410→280→220→180, workshop labour bottleneck,
    and land_network weak extra (+15 grain per epilogue turn vs labour×10 cap).
    Supports Control C (demand shift disabled) and Control L (legacies disabled) for harness.
    """

    turn_limit: int = EIGHT_TURN_LIMIT

    def __init__(
        self,
        seed: str = "seed-001",
        version: str = "1.0",
        start_state: GameState | None = None,
        disable_demand_shift: bool = False,
        disable_legacies: bool = False,
    ) -> None:
        self._seed = seed
        self._version = version
        self._disable_demand_shift = disable_demand_shift
        self._disable_legacies = disable_legacies
        # Agriculture phase owns its own FiveTurnGame
        self._agri = FiveTurnGame(seed=seed, version=version, start_state=start_state)
        self._state: GameState = self._agri.state
        self._history: list[TurnResolution] = []
        self._legacies: tuple[str, ...] = ()
        self._epilogue_started = False
        # Mirror rivals from agri for continuity
        self._rivals = self._agri._rivals  # type: ignore[attr-defined]
        self._rival_history = self._agri._rival_history  # type: ignore[attr-defined]

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

    @property
    def legacies(self) -> tuple[str, ...]:
        return self._legacies

    def _ensure_epilogue_start(self) -> None:
        if self._epilogue_started:
            return
        if len(self._history) < 5:
            return
        # Derive legacies at 5-turn boundary if not disabled
        if not self._disable_legacies:
            summary = self._agri.summary()
            self._legacies = derive_legacies(summary)
        else:
            self._legacies = ()
        # If Control C, add disable flag
        leg = list(self._legacies)
        if self._disable_demand_shift and "disable_demand_shift" not in leg:
            leg.append("disable_demand_shift")
        self._legacies = tuple(leg)
        # Compute starting labour: base 1 for all; river_contracts grants +2 (trade_heavy only)
        # This is the disruption: scarce labour goes to the strategy that did NOT dominate agriculture.
        # Granary NOT giving labour/efficiency — mastery of old bottleneck does not transfer.
        # Land Network remains weak (+15 grain vs labour×10 cap).
        base_labour = 1
        if "river_contracts" in self._legacies:
            base_labour += 2
        # Apply to state: copy with legacies and labour, and preserve other fields
        agri_state = self._agri.state
        new_player = PlayerState(
            cash=agri_state.player.cash,
            inventory=InventoryState(
                grain=agri_state.player.inventory.grain,
                finished_goods=agri_state.player.inventory.finished_goods,
            ),
            farm_capacity=agri_state.player.farm_capacity,
            storage_capacity=agri_state.player.storage_capacity,
            skilled_labour=base_labour,
        )
        self._state = GameState(
            turn=agri_state.turn,
            run_seed=agri_state.run_seed,
            ruleset_version=agri_state.ruleset_version,
            player=new_player,
            market=agri_state.market,
            river_market=agri_state.river_market,
            route=agri_state.route,
            legacies=self._legacies,
        )
        self._epilogue_started = True

    def _pressure_for_idx(self, idx: int) -> PressureState:
        if idx < 5:
            return pressure_for_turn(idx)
        # Epilogue: reuse normal pressure but with epilogue signal
        from app.domain.pressure import PressureState as PS

        # Use a valid PressureState (activation_turn 0..4 constraint) — reuse 4 with modified signal
        base = pressure_for_turn(4)
        return PS(
            pressure_id=base.pressure_id,
            stage="aftermath",
            activation_turn=4,
            world="normal",
            signal=f"City craft epilogue turn {idx - 4}/3 — urban demand shifts",
            title=f"Epilogue {idx - 4}",
        )

    def submit(self, command: PlayerCommand) -> TurnResolution:
        if self.is_complete:
            raise ValueError("game complete — no more decisions allowed (exactly 8 turns)")
        idx = len(self._history)
        # Delegate agriculture turns to inner FiveTurnGame for first 5
        if idx < 5:
            res = self._agri.submit(command)
            self._state = res.next_state
            # Keep legacies empty for agriculture turns
            self._history.append(res)
            # Sync state legacies (empty during agri)
            if idx == 4:
                # Just completed 5th turn, prepare epilogue start on next call
                self._ensure_epilogue_start()
            return res
        # Epilogue turns 5,6,7
        self._ensure_epilogue_start()
        # Land Network per-turn grain extra: +15 grain if space (weak vs labour cap)
        if "land_network" in self._legacies:
            from app.engine.actor import LAND_NETWORK_EXTRA_GRAIN_PER_TURN

            grain = self._state.player.inventory.grain
            cap = self._state.player.storage_capacity
            add = LAND_NETWORK_EXTRA_GRAIN_PER_TURN
            new_grain = grain + add
            if new_grain > cap:
                new_grain = cap
            if new_grain != grain:
                new_player = PlayerState(
                    cash=self._state.player.cash,
                    inventory=InventoryState(
                        grain=new_grain, finished_goods=self._state.player.inventory.finished_goods
                    ),
                    farm_capacity=self._state.player.farm_capacity,
                    storage_capacity=self._state.player.storage_capacity,
                    skilled_labour=self._state.player.skilled_labour,
                )
                self._state = GameState(
                    turn=self._state.turn,
                    run_seed=self._state.run_seed,
                    ruleset_version=self._state.ruleset_version,
                    player=new_player,
                    market=self._state.market,
                    river_market=self._state.river_market,
                    route=self._state.route,
                    legacies=self._state.legacies,
                )
        pressure = self._pressure_for_idx(idx)
        # Rivals still choose/ settle but with epilogue pressure (normal)
        # Use same two-phase as FiveTurnGame but without affecting supply (rivals isolated)

        # Build observable manually for epilogue
        if idx >= 5:
            # Use last pressure world (normal) and no threat
            from app.engine.rivals import ObservableContext as OC

            obs = OC(  # type: ignore
                turn=idx,
                world_now="normal",
                next_world_known=None,
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
        else:
            obs = self._agri._observable_for(idx)  # type: ignore
        mira_before = self._agri._rivals["mira"]  # type: ignore
        daran_before = self._agri._rivals["daran"]  # type: ignore
        from app.engine.rivals import DARAN_PROFILE as DP
        from app.engine.rivals import MIRA_PROFILE as MP
        from app.engine.rivals import choose_rival_command as crc

        mira_choice = crc(MP, mira_before, obs)
        daran_choice = crc(DP, daran_before, obs)
        ctx = self._state.to_turn_context()
        res = resolve_turn(self._state, command, pressure, ctx)
        self._history.append(res)
        self._state = res.next_state
        # Rival settlement
        from app.engine.rivals import SettlementContext as SC
        from app.engine.rivals import apply_rival_command as arc

        settlement = SC(
            world_now=pressure.world,
            home_price_pre=obs.home_price_pre,
            river_price_resolved=res.next_state.river_market.current_price,
            home_price_resolved=res.next_state.market.current_price,
            transport_cost_per_unit=obs.transport_cost_per_unit,
            route_capacity=obs.route_capacity,
            reliability_bps=obs.reliability_bps,
        )
        mira_result = arc(MP, mira_before, mira_choice, settlement)
        daran_result = arc(DP, daran_before, daran_choice, settlement)
        self._agri._rivals["mira"] = mira_result.after  # type: ignore
        self._agri._rivals["daran"] = daran_result.after  # type: ignore
        self._agri._rival_history.append((mira_result, daran_result))  # type: ignore
        return res

    def summary(self) -> StrategicSummary:
        # Reuse FiveTurnGame summary but with 8-turn history
        init = self._agri._initial_state  # type: ignore
        cash_vals = (
            [init.player.cash]
            + [h.next_state.player.cash for h in self._history]
            + [self._state.player.cash]
        )
        cash_low = min(cash_vals) if cash_vals else self._state.player.cash
        inv_vals = [init.player.inventory.grain] + [
            h.next_state.player.inventory.grain for h in self._history
        ]
        peak_inventory = max(inv_vals) if inv_vals else 0
        final_wealth = _wealth(self._state)
        initial_wealth = _wealth(init)
        wealth_delta_total = final_wealth - initial_wealth
        final_rivals = (self._agri._rivals["mira"], self._agri._rivals["daran"])  # type: ignore
        rival_hist = tuple(self._agri._rival_history)  # type: ignore
        return StrategicSummary(
            initial_state=init,
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
