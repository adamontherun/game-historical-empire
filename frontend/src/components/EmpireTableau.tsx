import { tableau } from "../lib/tableau";
import type { EmpireSummary } from "../api/types";

export function EmpireTableau({ empire }: { empire: EmpireSummary }) {
  const tiers = tableau(empire);
  return (
    <div className="card" data-testid="empire-tableau">
      <div className="section-label">Empire tableau</div>
      <div className="empire-tableau">
        {tiers.map((t) => (
          <div
            key={t.id}
            className={`empire-row ${t.reached ? "reached" : "ghost"}`}
            data-testid={`tier-${t.id}`}
            data-reached={t.reached ? "true" : "false"}
          >
            <span className="empire-row-label">{t.label}</span>
            <span className="empire-row-detail">{t.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
