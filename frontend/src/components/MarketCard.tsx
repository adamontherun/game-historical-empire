import { pricePerUnit } from "../lib/format";
import type { MarketView } from "../api/types";

// R2: price + Availability + Demand only; base_price/responsiveness not shown
export function MarketCard({
  title,
  market,
  variant,
}: {
  title: string;
  market: MarketView;
  variant: "home" | "river";
}) {
  return (
    <div className={`market-card ${variant}`} data-testid={`market-${variant}`}>
      <div className="market-title">{title}</div>
      <div className="market-price num">
        {pricePerUnit(market.current_price)} <small>/ grain</small>
      </div>
      <div className="market-meta">
        <span>
          <span>Availability</span> <span className="num">{market.supply}</span>
        </span>
        <span>
          <span>Demand</span> <span className="num">{market.demand}</span>
        </span>
      </div>
    </div>
  );
}
