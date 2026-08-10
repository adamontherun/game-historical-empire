import { signedPricePerUnit } from "../lib/format";
import type { RouteStatus } from "../api/types";

// R4: "Current route spread ..." — quote, not margin/profit — J4: one calm line in river colour, sign only on number
export function RouteLine({ route }: { route: RouteStatus }) {
  const isNegative = route.next_margin < 0;
  return (
    <div
      className={`route-line ${route.established ? "established" : ""}`}
      data-testid="route-line"
      data-established={route.established ? "true" : "false"}
      style={{ color: "var(--market-river)" }}
    >
      <span>{route.established ? "River route secured" : "River route: Closed"} — Current route spread </span>
      <span className="num" style={{ color: isNegative ? "var(--drought)" : "var(--gain)", fontWeight: 600 }}>
        {signedPricePerUnit(route.next_margin)}
      </span>
      <span> / grain</span>
    </div>
  );
}
