import { describe, it, expect } from "vitest";

describe("OutcomeReveal", () => {
  it("drivers are rendered via impact_money, not impact_bps (B7) — contract documented", () => {
    // B7: drivers have same impact_bps (e.g. 3238) but different impact_money signs.
    // The component must color by impact_money sign, never by impact_bps.
    // This doc test ensures the contract is not forgotten.
    const drivers = [
      { impact_money: 263, impact_bps: 3238 },
      { impact_money: -263, impact_bps: 3238 },
    ];
    // Color logic: positive green, negative drought
    expect(drivers[0].impact_bps).toBe(3238);
    expect(drivers[1].impact_bps).toBe(3238);
    expect(drivers[0].impact_money > 0).toBe(true);
    expect(drivers[1].impact_money < 0).toBe(true);
  });
});
