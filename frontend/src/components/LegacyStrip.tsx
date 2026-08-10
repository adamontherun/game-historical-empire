import type { LegacyView } from "../api/types";

export function LegacyStrip({ legacies }: { legacies: LegacyView[] }) {
  if (!legacies || legacies.length === 0) return null;
  return (
    <div className="card" data-testid="legacy-strip">
      <div className="section-label">Legacies — from the harvest years</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {legacies.map((l) => (
          <span
            key={l.id}
            data-testid={`legacy-${l.id}`}
            style={{
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "4px 8px",
              fontSize: 12,
              background: "var(--surface)",
            }}
            title={l.effect}
          >
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}
