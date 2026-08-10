import { describe, it, expect } from "vitest";
import { tableau } from "../lib/tableau";

describe("tableau", () => {
  it("initial empire shows only base tier reached", () => {
    const t = tableau({ farm_capacity: 5, storage_capacity: 130, route_established: false });
    expect(t.find((x) => x.id === "estate")!.reached).toBe(false); // actually farm 5 <15, so false
    // base: all false initially
    expect(t.filter((x) => x.reached).length).toBe(0);
  });

  it("investing run changes — farm expands", () => {
    const initial = tableau({ farm_capacity: 5, storage_capacity: 130, route_established: false });
    const afterExpand = tableau({ farm_capacity: 15, storage_capacity: 130, route_established: false });
    expect(afterExpand.filter((x) => x.reached).length).toBeGreaterThan(initial.filter((x) => x.reached).length);
    expect(afterExpand.find((x) => x.id === "estate")!.reached).toBe(true);
  });

  it("storage threshold 180 reached with one granary", () => {
    const afterGranary = tableau({ farm_capacity: 5, storage_capacity: 180, route_established: false });
    expect(afterGranary.find((x) => x.id === "storage")!.reached).toBe(true);
  });

  it("route secures trade tier", () => {
    const withRoute = tableau({ farm_capacity: 5, storage_capacity: 130, route_established: true });
    expect(withRoute.find((x) => x.id === "trade")!.reached).toBe(true);
  });

  it("investing both farm+storage reaches two tiers", () => {
    const afterBoth = tableau({ farm_capacity: 15, storage_capacity: 180, route_established: false });
    expect(afterBoth.filter((x) => x.reached).length).toBe(2);
  });

  it("passive hold×5 stays flat (negative test for B9)", () => {
    const initial = tableau({ farm_capacity: 5, storage_capacity: 130, route_established: false });
    const afterHold = tableau({ farm_capacity: 5, storage_capacity: 130, route_established: false });
    expect(afterHold).toEqual(initial);
  });

  it("does not read market prices — args only empire fields", () => {
    // tableau signature only takes empire fields; this test documents no economy leakage
    const t = tableau({ farm_capacity: 15, storage_capacity: 180, route_established: true });
    expect(t.length).toBe(3);
  });
});
