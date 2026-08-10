import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { formatRunRecord } from "../lib/runRecord";
import { CompletionSummary } from "../components/CompletionSummary";
import type { GameView } from "../api/types";

function makeGame(overrides: Partial<GameView> = {}): GameView {
  return {
    game_id: "g1",
    run_seed: "seed-abc-123",
    ruleset_version: "1.0.0",
    revision: 5,
    turn: 5,
    turn_limit: 5,
    signal: "done",
    pressure_stage: "aftermath",
    world: "normal",
    player_summary: { cash: 1000, inventory_grain: 10, farm_capacity: 15, storage_capacity: 180, wealth: 1000 },
    empire_summary: { farm_capacity: 15, storage_capacity: 180, route_established: true },
    home_valley_market: { supply: 0, demand: 0, base_price: 5000, current_price: 5000, responsiveness: 0 },
    river_town_market: { supply: 0, demand: 0, base_price: 5000, current_price: 5000, responsiveness: 0 },
    route_status: { established: true, capacity: 10, transport_cost_per_unit: 100, reliability_bps: 10000, next_margin: 0 },
    rival_headlines: { mira: "Mira did X", daran: "Daran did Y" },
    available_choices: [],
    latest_outcome: null,
    completion_summary: {
      initial_wealth: 5000,
      final_wealth: 6000,
      wealth_delta_total: 1000,
      final_cash: 800,
      final_grain: 20,
      final_farm_capacity: 15,
      final_storage_capacity: 180,
      cash_low: 400,
      peak_inventory: 50,
      is_complete: true,
      final_rival_headlines: { mira: "Mira final", daran: "Daran final" },
    },
    ...overrides,
  };
}

describe("formatRunRecord", () => {
  it("records ordered choice ids verbatim using exact server ids", () => {
    const ids = ["buy_grain:55", "hold", "ship_grain:10", "sell_grain:999", "expand_farm"];
    const s = formatRunRecord("seed-abc-123", "1.0.0", ids);
    // must contain seed and rules
    expect(s).toContain("seed=seed-abc-123");
    expect(s).toContain("rules=1.0.0");
    // must contain ids in order
    const idx = ids.map((id) => s.indexOf(id));
    for (let i = 0; i < idx.length; i++) expect(idx[i]).toBeGreaterThanOrEqual(0);
    for (let i = 1; i < idx.length; i++) expect(idx[i]).toBeGreaterThan(idx[i - 1]);
    // must not be reconstructible from kind+quantity alone — hold has no quantity,
    // ship_grain:10 vs buy_grain:55 share quantity 55 would collide if reconstructed
    // This assertion fails if someone does `kind + ":" + quantity`
    void ids.map((id) => {
      const [kind, qty] = id.split(":");
      return qty ? `${kind}:${qty}` : kind;
    });
    expect(s).toContain("hold");
    expect(s).not.toContain("hold:null");
    expect(s).not.toContain("hold:0");
  });

  it("fails if reconstructed from kind+quantity instead of exact id", () => {
    // Simulate a bug where ids are reconstructed as `${kind}:${quantity}`
    const serverIds = ["buy_grain:55", "sell_grain:7", "hold"];
    // A buggy formatter would do:
    const buggy = serverIds
      .map((id) => {
        const parts = id.split(":");
        const kind = parts[0];
        const qty = parts[1] ?? null;
        // bug: reconstructs, loses exactness for hold
        return qty ? `${kind}:${qty}` : `${kind}:null`;
      })
      .join(",");
    const correct = formatRunRecord("s", "r", serverIds);
    // correct must not contain the buggy artefact
    expect(correct).not.toContain("hold:null");
    expect(buggy).toContain("hold:null");
    // correct must contain exact ids
    expect(correct).toContain("buy_grain:55");
    expect(correct).toContain("hold");
  });
});

describe("CompletionSummary copy fallback", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("copy fallback does not throw and logs no console error when clipboard is undefined", async () => {
    const user = userEvent.setup();
    // jsdom navigator.clipboard is a getter-only — stub via defineProperty
    vi.stubGlobal("navigator", { ...navigator, clipboard: undefined } as unknown as Navigator);
    Object.defineProperty(window.navigator, "clipboard", { value: undefined, configurable: true });
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const game = makeGame();
    render(<CompletionSummary game={game} choiceIds={["hold", "buy_grain:55"]} onPlayAgain={vi.fn()} />);
    const btn = screen.getByTestId("copy-run-record");
    // should not throw
    await expect(user.click(btn)).resolves.not.toThrow();
    expect(errSpy).not.toHaveBeenCalled();
  });

  it("renders run record containing seed, rules, and ordered choice ids", () => {
    const game = makeGame({ run_seed: "my-seed-xyz", ruleset_version: "9.9.9" });
    const ids = ["expand_farm", "build_granary", "hold", "hold", "hold"];
    render(<CompletionSummary game={game} choiceIds={ids} onPlayAgain={vi.fn()} />);
    const block = screen.getByTestId("run-record-replay");
    expect(block.textContent).toContain("my-seed-xyz");
    expect(block.textContent).toContain("9.9.9");
    for (const id of ids) expect(block.textContent).toContain(id);
    // order check
    const text = block.textContent!;
    expect(text.indexOf("expand_farm")).toBeLessThan(text.indexOf("build_granary"));
  });
});
