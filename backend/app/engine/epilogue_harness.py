"""Four-arm epilogue harness — Section 13 AC1 measurement.

Arms (paired, same seeds):
  A: agriculture only (5 turns, FiveTurnGame)
  B: agriculture + epilogue full (8 turns, EightTurnGame)
  C: agriculture + epilogue without demand shift (disable_demand_shift=True)
  L: agriculture + epilogue without legacies (disable_legacies=True)

Same POLICY_IDS, same start states, same first-5 policy code; only epilogue differs.
AC1 PASS iff P_agri loses rank or contracts >=40% in B vs A AND Control C does NOT pass.
Net-positive guard: ∃ intentional pid with median_B > median_A.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.domain.types import GameState, PlayerCommand
from app.engine.harness import POLICY_FUNCS, BatchConfig
from app.engine.prototype import EightTurnGame, FiveTurnGame, default_start_state


def _epilogue_command(state: GameState) -> PlayerCommand:
    """Uniform epilogue policy: craft if possible, else sell finished, else sell grain/hold.

    Shared across all policies for fairness — not a per-policy invention.
    """
    labour = state.player.skilled_labour
    grain = state.player.inventory.grain
    finished = state.player.inventory.finished_goods
    # Labour bottleneck visible: craft capped by labour*10
    if labour > 0 and grain > 0:
        max_by_labour = labour * 10
        qty = min(grain, max_by_labour)
        # Keep quantities reasonable for trace
        if qty > 60:
            qty = 60
        if qty > 0:
            return PlayerCommand.model_validate({"type": "craft_goods", "quantity": qty})
    if finished > 0:
        qty = min(finished, 30)
        if qty > 0:
            return PlayerCommand.model_validate({"type": "sell_finished_goods", "quantity": qty})
    if grain > 0:
        # Sell raw at degraded price — shows decay
        qty = min(grain, 20)
        if qty > 0:
            return PlayerCommand.model_validate({"type": "sell_grain", "quantity": qty})
    return PlayerCommand.model_validate({"type": "hold"})


class FourArmResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    config: BatchConfig
    arm_a_medians: dict[str, int]
    arm_b_medians: dict[str, int]
    arm_c_medians: dict[str, int]
    arm_l_medians: dict[str, int]
    p_agri: str
    lead_a: int
    lead_b: int
    lead_c: int
    contraction_b: int
    contraction_c: int
    rank_a: int
    rank_b: int
    rank_c: int
    rank_l: int
    ac1_pass: bool
    ac1_control_c_pass: bool
    ac1_credible: bool
    net_positive_pass: bool
    net_positive_best_gain: int
    arm_a_ratio_bps: int
    arm_b_ratio_bps: int


def _median(vals: list[int]) -> int:
    s = sorted(vals)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) // 2


def run_four_arm(config: BatchConfig) -> FourArmResult:
    seeds = [f"{config.seed_prefix}-{i:04d}" for i in range(config.n_seeds)]
    # Collect per-policy wealths per arm
    wealths_a: dict[str, list[int]] = {pid: [] for pid in config.policy_ids}
    wealths_b: dict[str, list[int]] = {pid: [] for pid in config.policy_ids}
    wealths_c: dict[str, list[int]] = {pid: [] for pid in config.policy_ids}
    wealths_l: dict[str, list[int]] = {pid: [] for pid in config.policy_ids}

    for seed in seeds:
        for pid in config.policy_ids:
            func = POLICY_FUNCS[pid]
            # Arm A: 5 turns
            g_a = FiveTurnGame(
                seed=seed,
                version=config.version,
                start_state=default_start_state(seed, config.version),
            )
            for ti in range(5):
                cmd = func(g_a.state, ti, seed, config.version)
                g_a.submit(cmd)
            wealths_a[pid].append(g_a.summary().final_wealth)

            # Arm B: 8 turns full
            g_b = EightTurnGame(
                seed=seed,
                version=config.version,
                start_state=default_start_state(seed, config.version),
            )
            for ti in range(5):
                cmd = func(g_b.state, ti, seed, config.version)
                g_b.submit(cmd)
            for _ti in range(5, 8):
                cmd = _epilogue_command(g_b.state)
                g_b.submit(cmd)
            wealths_b[pid].append(g_b.summary().final_wealth)

            # Arm C: demand shift disabled
            g_c = EightTurnGame(
                seed=seed,
                version=config.version,
                start_state=default_start_state(seed, config.version),
                disable_demand_shift=True,
            )
            for ti in range(5):
                cmd = func(g_c.state, ti, seed, config.version)
                g_c.submit(cmd)
            for _ti in range(5, 8):
                cmd = _epilogue_command(g_c.state)
                g_c.submit(cmd)
            wealths_c[pid].append(g_c.summary().final_wealth)

            # Arm L: legacies disabled
            g_l = EightTurnGame(
                seed=seed,
                version=config.version,
                start_state=default_start_state(seed, config.version),
                disable_legacies=True,
            )
            for ti in range(5):
                cmd = func(g_l.state, ti, seed, config.version)
                g_l.submit(cmd)
            for _ti in range(5, 8):
                cmd = _epilogue_command(g_l.state)
                g_l.submit(cmd)
            wealths_l[pid].append(g_l.summary().final_wealth)

    # Medians
    med_a = {pid: _median(wealths_a[pid]) for pid in config.policy_ids}
    med_b = {pid: _median(wealths_b[pid]) for pid in config.policy_ids}
    med_c = {pid: _median(wealths_c[pid]) for pid in config.policy_ids}
    med_l = {pid: _median(wealths_l[pid]) for pid in config.policy_ids}

    # Intentional ranking
    intentional = ("production_heavy", "storage_heavy", "trade_heavy", "cash_preserving")
    # Filter to intentional present in config
    int_ids = [pid for pid in intentional if pid in config.policy_ids]
    # Identify P_agri from Arm A
    sorted_a = sorted(int_ids, key=lambda pid: -med_a[pid])
    p_agri = sorted_a[0] if sorted_a else ""
    # Ranks in each arm
    sorted_b = sorted(int_ids, key=lambda pid: -med_b[pid])
    sorted_c = sorted(int_ids, key=lambda pid: -med_c[pid])
    sorted_l = sorted(int_ids, key=lambda pid: -med_l[pid])
    rank_a = sorted_a.index(p_agri) + 1 if p_agri in sorted_a else 99
    rank_b = sorted_b.index(p_agri) + 1 if p_agri in sorted_b else 99
    rank_c = sorted_c.index(p_agri) + 1 if p_agri in sorted_c else 99
    rank_l = sorted_l.index(p_agri) + 1 if p_agri in sorted_l else 99
    # Leads: top vs second in each arm
    meds_a_sorted = sorted([med_a[pid] for pid in int_ids], reverse=True)
    meds_b_sorted = sorted([med_b[pid] for pid in int_ids], reverse=True)

    # lead for P_agri specifically vs its runner-up in same arm
    # For B/C, runner-up is second overall if P_agri is rank1, else top overall if P_agri not rank1 (lead negative)
    def lead_for(p: str, med: dict[str, int], sorted_ids: list[str]) -> int:
        if not sorted_ids:
            return 0
        if sorted_ids[0] == p:
            # P is top, second is sorted[1] if exists
            if len(sorted_ids) >= 2:
                return med[p] - med[sorted_ids[1]]
            return 0
        # P not top, lead is negative: med[p] - med[top]
        return med[p] - med[sorted_ids[0]]

    lead_a = lead_for(p_agri, med_a, sorted_a)
    lead_b = lead_for(p_agri, med_b, sorted_b)
    lead_c = lead_for(p_agri, med_c, sorted_c)
    # Contractions
    contraction_b = (lead_a - lead_b) * 100 // max(lead_a, 1) if lead_a != 0 else 0
    contraction_c = (lead_a - lead_c) * 100 // max(lead_a, 1) if lead_a != 0 else 0
    # AC1: P loses rank or contracts >=40% in B
    ac1_b_pass = (rank_b >= 2) or (contraction_b >= 40)
    ac1_c_pass = (rank_c >= 2) or (contraction_c >= 40)
    ac1_credible = ac1_b_pass and not ac1_c_pass
    # Net-positive: ∃ pid with median_B > median_A
    gains = [med_b[pid] - med_a[pid] for pid in int_ids]
    best_gain = max(gains) if gains else -999999
    net_positive_pass = any(med_b[pid] > med_a[pid] for pid in int_ids)

    # Ratios
    def ratio_bps(meds: list[int]) -> int:
        if len(meds) >= 2 and meds[1] != 0:
            return meds[0] * 10_000 // meds[1]
        return 99_999

    ratio_a = ratio_bps(meds_a_sorted)
    ratio_b = ratio_bps(meds_b_sorted)

    return FourArmResult(
        config=config,
        arm_a_medians=med_a,
        arm_b_medians=med_b,
        arm_c_medians=med_c,
        arm_l_medians=med_l,
        p_agri=p_agri,
        lead_a=lead_a,
        lead_b=lead_b,
        lead_c=lead_c,
        contraction_b=contraction_b,
        contraction_c=contraction_c,
        rank_a=rank_a,
        rank_b=rank_b,
        rank_c=rank_c,
        rank_l=rank_l,
        ac1_pass=ac1_b_pass,
        ac1_control_c_pass=ac1_c_pass,
        ac1_credible=ac1_credible,
        net_positive_pass=net_positive_pass,
        net_positive_best_gain=best_gain,
        arm_a_ratio_bps=ratio_a,
        arm_b_ratio_bps=ratio_b,
    )


def format_four_arm(result: FourArmResult) -> str:
    lines: list[str] = []
    lines.append(
        f"# Four-Arm Harness — {result.config.n_seeds} seeds × {len(result.config.policy_ids)} policies"
    )
    lines.append(f"Config: prefix={result.config.seed_prefix} version={result.config.version}")
    lines.append("")
    for arm_name, med in [
        ("Arm A (5 turns agri)", result.arm_a_medians),
        ("Arm B (8 full)", result.arm_b_medians),
        ("Control C (demand OFF)", result.arm_c_medians),
        ("Control L (legacies OFF)", result.arm_l_medians),
    ]:
        part = ", ".join(f"{pid}={med[pid]}" for pid in sorted(med))
        lines.append(f"{arm_name}: {part}")
    lines.append("")
    lines.append(
        f"P_agri = {result.p_agri} rank A={result.rank_a} B={result.rank_b} C={result.rank_c} L={result.rank_l}"
    )
    lines.append(f"lead_A={result.lead_a} lead_B={result.lead_b} lead_C={result.lead_c}")
    lines.append(f"contraction_B={result.contraction_b}% contraction_C={result.contraction_c}%")
    lines.append(
        f"AC1 B pass (rank>=2 or C>=40): {result.ac1_pass}  Control C pass: {result.ac1_control_c_pass}  AC1 credible (B and not C): {result.ac1_credible} — {'PASS' if result.ac1_credible else 'FAIL'}"
    )
    lines.append(
        f"Net-positive guard (some B>A): {result.net_positive_pass} best_gain={result.net_positive_best_gain} — {'PASS' if result.net_positive_pass else 'FAIL'}"
    )
    lines.append(f"Ratios bps: A={result.arm_a_ratio_bps} B={result.arm_b_ratio_bps}")
    return "\n".join(lines)
