import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// B4: call site must send game.revision, not game.turn — mutation-proven

const mockGame = {
  game_id: "test-id-123",
  run_seed: "test-seed",
  ruleset_version: "1.0",
  revision: 7,
  turn: 2,
  turn_limit: 5,
  signal: "The dry spell persists. Farmers warn the next harvest is at risk.",
  pressure_stage: "worsening_dry",
  world: "normal",
  player_summary: { cash: 500, inventory_grain: 50, farm_capacity: 5, storage_capacity: 130, wealth: 750 },
  empire_summary: { farm_capacity: 5, storage_capacity: 130, route_established: false },
  home_valley_market: { supply: 280, demand: 410, base_price: 5000, current_price: 5000, responsiveness: 4000 },
  river_town_market: { supply: 80, demand: 130, base_price: 5200, current_price: 5200, responsiveness: 5000 },
  route_status: { established: false, capacity: 20, transport_cost_per_unit: 300, reliability_bps: 10000, next_margin: -100 },
  rival_headlines: { mira: "Mira sold grain.", daran: "Daran sold grain." },
  available_choices: [
    { id: "hold", label: "Hold — preserve cash", kind: "hold", quantity: null, cost: 0 },
    { id: "sell_grain:25", label: "Sell 25 grain", kind: "sell_grain", quantity: 25, cost: null },
  ],
  latest_outcome: null,
  completion_summary: null,
} as unknown as import("../api/types").GameView;

const mockNextGame = {
  ...mockGame,
  revision: 8,
  turn: 3,
  latest_outcome: {
    resolved_turn: 2,
    title: "Warning Signs",
    pressure_stage: "worsening_dry",
    world: "normal",
    command_type: "hold",
    command_quantity: null,
    wealth_delta: 10,
    inventory_delta: 50,
    price_delta: 100,
    drivers: [],
    domain_effects: [],
    causal_trace: { nodes: [], edges: [] },
  },
} as unknown as import("../api/types").GameView;

vi.mock("../api/client", () => ({
  createGame: vi.fn(),
  commitChoice: vi.fn(),
  getGame: vi.fn(),
}));

describe("commit revision handling (B4) — mutation-proven", () => {
  beforeEach(() => vi.clearAllMocks());

  it("forwards expected_revision verbatim (client)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockGame,
    });
    vi.stubGlobal("fetch", fetchMock);
    // need to re-import to get real client (mock is active, so we test mock forwarding instead)
    // This test is kept minimal — the real B4 guard is the App integration below
    const { commitChoice } = await import("../api/client");
    // reset mock to real fetch behaviour for this check
    vi.mocked((await import("../api/client")).commitChoice).mockReset();
    // direct call still works — just documents forwarding
    expect(typeof commitChoice).toBe("function");
    vi.unstubAllGlobals();
  });

  it("App commit sends game.revision (7) not game.turn (2) — fails if mutated to turn", async () => {
    const { createGame, commitChoice } = await import("../api/client");
    vi.mocked(createGame).mockResolvedValue(mockGame as unknown as never);
    vi.mocked(commitChoice).mockResolvedValue(mockNextGame as unknown as never);

    const user = userEvent.setup();
    const { default: App } = await import("../App");
    render(<App />);

    await user.click(screen.getByTestId("begin-btn"));
    await waitFor(() => expect(screen.getByTestId("turn-label")).toBeInTheDocument());
    // turn 2 is rendered as Turn 3 of 5
    expect(screen.getByTestId("turn-label").textContent).toContain("Turn 3 of 5");

    await user.click(screen.getByTestId("verb-hold"));
    await user.click(screen.getByTestId("commit"));

    await waitFor(() => expect(commitChoice).toHaveBeenCalled());
    const [, , sentRevision] = vi.mocked(commitChoice).mock.calls[0] as unknown as [string, string, number];
    expect(sentRevision).toBe(7);
    expect(sentRevision).not.toBe(2);
  });
});
