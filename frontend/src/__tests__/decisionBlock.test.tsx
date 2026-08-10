import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionBlock } from "../components/DecisionBlock";
import type { ChoiceView } from "../api/types";

describe("DecisionBlock", () => {
  it("renders quantities verbatim from payload (B1) — sell 7 and 999", async () => {
    const choices: ChoiceView[] = [
      { id: "hold", label: "Hold — preserve cash", kind: "hold", quantity: null, cost: 0 },
      { id: "sell_grain:7", label: "Sell 7 grain", kind: "sell_grain", quantity: 7, cost: null },
      { id: "sell_grain:999", label: "Sell 999 grain", kind: "sell_grain", quantity: 999, cost: null },
    ];
    const onSelect = vi.fn();
    render(<DecisionBlock choices={choices} selectedId={null} onSelect={onSelect} committing={false} onCommit={vi.fn()} />);
    expect(screen.getByTestId("qty-sell_grain:7")).toBeInTheDocument();
    expect(screen.getByTestId("qty-sell_grain:999")).toBeInTheDocument();
    expect(screen.getByTestId("qty-sell_grain:7").textContent).toBe("7");
    expect(screen.getByTestId("qty-sell_grain:999").textContent).toBe("999");
  });

  it("submits exact server id, never reconstructs (B1)", async () => {
    const user = userEvent.setup();
    const choices: ChoiceView[] = [
      { id: "buy_grain:55", label: "Buy 55 grain — 275 cash", kind: "buy_grain", quantity: 55, cost: 275 },
      { id: "buy_grain:110", label: "Buy 110 grain — 550 cash", kind: "buy_grain", quantity: 110, cost: 550 },
    ];
    const onSelect = vi.fn();
    render(<DecisionBlock choices={choices} selectedId={null} onSelect={onSelect} committing={false} onCommit={vi.fn()} />);
    await user.click(screen.getByTestId("qty-buy_grain:55"));
    expect(onSelect).toHaveBeenCalledWith("buy_grain:55");
  });

  it("shows hold cost 0 (cost !== null, not truthiness) (B6)", () => {
    const choices: ChoiceView[] = [
      { id: "hold", label: "Hold — preserve cash", kind: "hold", quantity: null, cost: 0 },
      { id: "sell_grain:10", label: "Sell 10 grain", kind: "sell_grain", quantity: 10, cost: null },
    ];
    render(<DecisionBlock choices={choices} selectedId={null} onSelect={vi.fn()} committing={false} onCommit={vi.fn()} />);
    // hold cost 0 must be visible
    expect(screen.getByText("Cost: 0 coins")).toBeInTheDocument();
    // sell has no cost line — only hold's
    const costs = screen.getAllByText(/Cost:/);
    expect(costs).toHaveLength(1);
  });

  it("renders ChoiceView.label as authoritative (B6)", () => {
    const choices: ChoiceView[] = [
      { id: "sell_grain:20", label: "Sell 20 grain", kind: "sell_grain", quantity: 20, cost: null },
    ];
    render(<DecisionBlock choices={choices} selectedId={null} onSelect={vi.fn()} committing={false} onCommit={vi.fn()} />);
    expect(screen.getByText("Sell 20 grain")).toBeInTheDocument();
  });

  it("groups by kind — 9 choices collapse to 6 cards (B1)", () => {
    const choices: ChoiceView[] = [
      { id: "hold", label: "Hold", kind: "hold", quantity: null, cost: 0 },
      { id: "expand_farm", label: "Expand", kind: "expand_farm", quantity: null, cost: 500 },
      { id: "build_granary", label: "Granary", kind: "build_granary", quantity: null, cost: 300 },
      { id: "buy_grain:30", label: "Buy 30", kind: "buy_grain", quantity: 30, cost: 177 },
      { id: "buy_grain:60", label: "Buy 60", kind: "buy_grain", quantity: 60, cost: 355 },
      { id: "sell_grain:35", label: "Sell 35", kind: "sell_grain", quantity: 35, cost: null },
      { id: "sell_grain:70", label: "Sell 70", kind: "sell_grain", quantity: 70, cost: null },
      { id: "ship_grain:10", label: "Ship 10", kind: "ship_grain", quantity: 10, cost: null },
      { id: "ship_grain:20", label: "Ship 20", kind: "ship_grain", quantity: 20, cost: null },
    ];
    render(<DecisionBlock choices={choices} selectedId={null} onSelect={vi.fn()} committing={false} onCommit={vi.fn()} />);
    expect(screen.getByTestId("verb-hold")).toBeInTheDocument();
    expect(screen.getByTestId("verb-buy_grain")).toBeInTheDocument();
    expect(screen.getByTestId("verb-sell_grain")).toBeInTheDocument();
    expect(screen.getByTestId("verb-ship_grain")).toBeInTheDocument();
    // 6 verb cards
    const verbs = screen.getAllByTestId(/^verb-/);
    expect(verbs).toHaveLength(6);
  });
});
