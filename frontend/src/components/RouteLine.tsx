import { signedPricePerUnit } from "../lib/format";
import type { RouteStatus } from "../api/types";

// R4: "Current route spread ..." — quote, not margin/profit
export function RouteLine({ route }: { route: RouteStatus }) {
  const isNegative = route.next_margin < 0;
  return (
    <div
      className={`route-line ${route.established ? "established" : ""} ${isNegative ? "negative" : ""}`}
      data-testid="route-line"
      data-established={route.established ? "true" : "false"}
    >
      <span>{route.established ? "River route secured" : "River route: Closed"}</span>
      <span className="num">Current route spread {signedPricePerUnit(route.next_margin)} / grain</span>
      <span className="num" style={{ opacity: 0.7 }}>
        cap {route.capacity}
      </span>
    </div>
  );
}
