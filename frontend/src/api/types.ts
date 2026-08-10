// Minimal GameView shapes — mirrors backend/app/api/schemas.py
// Frontend consumes these verbatim; no economy recomputation.

export type ChoiceView = {
  id: string;
  label: string;
  kind: string;
  quantity: number | null;
  cost: number | null;
};

export type PlayerSummary = {
  cash: number;
  inventory_grain: number;
  farm_capacity: number;
  storage_capacity: number;
  wealth: number;
};

export type EmpireSummary = {
  farm_capacity: number;
  storage_capacity: number;
  route_established: boolean;
};

export type MarketView = {
  supply: number;
  demand: number;
  base_price: number;
  current_price: number;
  responsiveness: number;
};

export type RouteStatus = {
  established: boolean;
  capacity: number;
  transport_cost_per_unit: number;
  reliability_bps: number;
  next_margin: number;
};

export type RivalHeadlines = {
  mira: string;
  daran: string;
};

export type OutcomeDriver = {
  id: string;
  label: string;
  kind: string;
  impact_money: number;
  impact_bps: number;
  reason_code: string;
  causal_node_ids: string[];
};

export type DomainEffect = {
  metric: string;
  before: number;
  after: number;
  delta: number;
  reason_code: string;
};

export type CausalNode = {
  id: string;
  label: string;
  kind: string;
  before: number | null;
  after: number | null;
  delta: number | null;
  reason_code: string;
  parent_ids: string[];
};

export type CausalTrace = {
  nodes: CausalNode[];
  edges: [string, string][];
};

export type OutcomeView = {
  resolved_turn: number;
  title: string;
  pressure_stage: string;
  world: "normal" | "drought";
  command_type: string;
  command_quantity: number | null;
  wealth_delta: number;
  inventory_delta: number;
  price_delta: number;
  drivers: OutcomeDriver[];
  domain_effects: DomainEffect[];
  causal_trace: CausalTrace;
};

export type CompletionSummaryView = {
  initial_wealth: number;
  final_wealth: number;
  wealth_delta_total: number;
  final_cash: number;
  final_grain: number;
  final_farm_capacity: number;
  final_storage_capacity: number;
  cash_low: number;
  peak_inventory: number;
  is_complete: boolean;
  final_rival_headlines: RivalHeadlines | null;
};

export type LegacyView = {
  id: string;
  label: string;
  effect: string;
};

export type GameView = {
  game_id: string;
  run_seed: string;
  ruleset_version: string;
  revision: number;
  turn: number;
  turn_limit: number;
  signal: string;
  pressure_stage: string;
  world: "normal" | "drought";
  player_summary: PlayerSummary;
  empire_summary: EmpireSummary;
  home_valley_market: MarketView;
  river_town_market: MarketView;
  route_status: RouteStatus;
  rival_headlines: RivalHeadlines | null;
  available_choices: ChoiceView[];
  latest_outcome: OutcomeView | null;
  completion_summary: CompletionSummaryView | null;
  skilled_labour?: number | null;
  finished_goods?: number | null;
  finished_goods_price?: number | null;
  legacies?: LegacyView[] | null;
  is_epilogue?: boolean | null;
  epilogue_turn?: number | null;
};
