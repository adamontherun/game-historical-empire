/**
 * Pure presentation function mapping EmpireSummary to tier rows.
 * Three independent milestones per R1 — no arrows, no implied ordering.
 * Thresholds justified from measured default_start_state:
 *   farm 5 +10 per expand_farm (cost 500), storage 130 +50 per granary (cost 300), route false→true.
 */

export type Empire = {
  farm_capacity: number;
  storage_capacity: number;
  route_established: boolean;
  skilled_labour?: number | null;
};

export type Tier = {
  id: string;
  label: string;
  detail: string;
  reached: boolean;
};

export function tableau(empire: Empire): Tier[] {
  const rows: Tier[] = [
    {
      id: "estate",
      label: "Estate",
      detail:
        empire.farm_capacity >= 15
          ? `Expanded Estate · Farm ${empire.farm_capacity}`
          : `Family Farm · Farm ${empire.farm_capacity}`,
      reached: empire.farm_capacity >= 15,
    },
    {
      id: "storage",
      label: "Storage",
      detail:
        empire.storage_capacity >= 180
          ? `Granary Network · Storage ${empire.storage_capacity}`
          : `Granary ${empire.storage_capacity}`,
      reached: empire.storage_capacity >= 180,
    },
    {
      id: "trade",
      label: "Trade",
      detail: empire.route_established ? "River access: Secured" : "River access: Closed",
      reached: empire.route_established,
    },
  ];
  // Section 13 — workshop row (visible when skilled_labour present, even if 0, to show bottleneck)
  if (empire.skilled_labour !== undefined && empire.skilled_labour !== null) {
    const labour = empire.skilled_labour;
    rows.push({
      id: "workshop",
      label: "Workshop",
      detail: labour > 0 ? `Skilled hands ${labour} · can craft ${labour * 10} grain/turn` : "No skilled hands",
      reached: labour > 0,
    });
  }
  return rows;
}
