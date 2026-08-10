import type { MarketView, RouteStatus } from "../api/types";
import { MarketCard } from "./MarketCard";
import { RouteLine } from "./RouteLine";

export function MarketPulse({
  home,
  river,
  route,
}: {
  home: MarketView;
  river: MarketView;
  route: RouteStatus;
}) {
  return (
    <div className="card" data-testid="market-pulse">
      <div className="section-label">Markets</div>
      <div className="market-pulse">
        <MarketCard title="Home Valley" market={home} variant="home" />
        <MarketCard title="River Town" market={river} variant="river" />
        <RouteLine route={route} />
      </div>
    </div>
  );
}
