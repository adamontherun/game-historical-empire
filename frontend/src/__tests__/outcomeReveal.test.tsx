import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { OutcomeReveal } from "../components/OutcomeReveal";
import type { GameView } from "../api/types";

// I3: B7 is unverified unless component is rendered — this test must fail if OutcomeReveal deleted or colours by impact_bps

function mkGameWithDrivers(): GameView {
  return {
    game_id: "test-id",
    run_seed: "playtest-1",
    ruleset_version: "1.0",
    revision: 3,
    turn: 3,
    turn_limit: 5,
    signal: "Drought cuts farm output — regional supply tightens.",
    pressure_stage: "aftermath",
    world: "normal",
    player_summary: { cash: 500, inventory_grain: 70, farm_capacity: 5, storage_capacity: 130, wealth: 850 },
    empire_summary: { farm_capacity: 5, storage_capacity: 130, route_established: false },
    home_valley_market: { supply: 280, demand: 410, base_price: 5000, current_price: 5928, responsiveness: 4000 },
    river_town_market: { supply: 80, demand: 130, base_price: 5200, current_price: 6240, responsiveness: 5000 },
    route_status: { established: false, capacity: 20, transport_cost_per_unit: 300, reliability_bps: 10000, next_margin: -100 },
    rival_headlines: { mira: "Mira sold grain at market.", daran: "Daran sold grain at market." },
    available_choices: [],
    latest_outcome: {
      resolved_turn: 3,
      title: "Drought",
      pressure_stage: "drought",
      world: "drought",
      command_type: "hold",
      command_quantity: null,
      wealth_delta: 10,
      inventory_delta: 20,
      price_delta: 309,
      drivers: [
        {
          id: "driver_pos",
          label: "Harvest gain +263",
          kind: "valuation",
          impact_money: 263,
          impact_bps: 3238,
          reason_code: "x",
          causal_node_ids: [],
        },
        {
          id: "driver_neg",
          label: "Cash cost -263",
          kind: "cash",
          impact_money: -263,
          impact_bps: 3238,
          reason_code: "y",
          causal_node_ids: [],
        },
      ],
      domain_effects: [],
      causal_trace: { nodes: [], edges: [] },
    },
    completion_summary: null,
  } as unknown as GameView;
}

describe("OutcomeReveal — B7 mutation-proven (I3)", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener: () => {}, removeEventListener: () => {} }));
  });

  it("renders drivers verbatim and colours by impact_money, not impact_bps", async () => {
    const game = mkGameWithDrivers();
    render(<OutcomeReveal game={game} onContinue={() => {}} onFinish={() => {}} />);

    // drivers must be rendered
    expect(screen.getByTestId("driver-driver_pos")).toBeInTheDocument();
    expect(screen.getByTestId("driver-driver_neg")).toBeInTheDocument();

    // labels verbatim
    expect(screen.getByText("Harvest gain +263")).toBeInTheDocument();
    expect(screen.getByText("Cash cost -263")).toBeInTheDocument();

    // impact_money sign determines colour — both have same impact_bps (3238) so bps cannot distinguish
    const posImpact = screen.getByTestId("driver-driver_pos").querySelector(".impact")!;
    const negImpact = screen.getByTestId("driver-driver_neg").querySelector(".impact")!;
    expect(posImpact.classList.contains("positive")).toBe(true);
    expect(negImpact.classList.contains("negative")).toBe(true);
    expect(posImpact.textContent).toContain("+263");
    expect(negImpact.textContent).toContain("−263");
  });

  it("does not render percentage-of-total or residual (B7)", async () => {
    const game = mkGameWithDrivers();
    render(<OutcomeReveal game={game} onContinue={() => {}} onFinish={() => {}} />);
    // no element should contain % or residual
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/residual/i)).not.toBeInTheDocument();
    // beat label is Top drivers without (≤3)
    expect(screen.getByText("Top drivers")).toBeInTheDocument();
    expect(screen.queryByText(/≤3/)).not.toBeInTheDocument();
  });

  it("world beat shows single stage indicator, not duplicated enums (I8)", async () => {
    const game = mkGameWithDrivers();
    render(<OutcomeReveal game={game} onContinue={() => {}} onFinish={() => {}} />);
    const beatWorld = screen.getByTestId("beat-world");
    // should contain single capitalized stage, not "drought · drought"
    expect(beatWorld.textContent).not.toMatch(/drought.*·.*drought/i);
    expect(beatWorld.textContent?.toLowerCase()).toContain("drought");
  });

  it("numbers beat hides zero deltas (I12)", async () => {
    const game = mkGameWithDrivers();
    // set one delta to 0
    game.latest_outcome!.inventory_delta = 0;
    render(<OutcomeReveal game={game} onContinue={() => {}} onFinish={() => {}} />);
    const beatNumbers = screen.getByTestId("beat-numbers");
    expect(beatNumbers.textContent).not.toContain("Grain");
    expect(beatNumbers.textContent).toContain("Wealth");
    expect(beatNumbers.textContent).toContain("Home price");
  });
});
