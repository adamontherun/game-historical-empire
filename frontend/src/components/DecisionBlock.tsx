import { useState, useMemo } from "react";
import type { ChoiceView } from "../api/types";

type Group = {
  kind: string;
  choices: ChoiceView[];
};

function groupByKind(choices: ChoiceView[]): Group[] {
  const map = new Map<string, ChoiceView[]>();
  const order: string[] = [];
  for (const c of choices) {
    if (!map.has(c.kind)) {
      map.set(c.kind, []);
      order.push(c.kind);
    }
    map.get(c.kind)!.push(c);
  }
  return order.map((kind) => ({ kind, choices: map.get(kind)! }));
}

export function DecisionBlock({
  choices,
  selectedId,
  onSelect,
  committing,
  onCommit,
}: {
  choices: ChoiceView[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  committing: boolean;
  onCommit: () => void;
}) {
  const groups = useMemo(() => groupByKind(choices), [choices]);
  const [qtyChoice, setQtyChoice] = useState<Map<string, string>>(new Map());

  // default quantity = largest quantity in group (or first if no quantity)
  const effectiveId = (g: Group): string => {
    if (g.choices.length === 1) return g.choices[0].id;
    const chosen = qtyChoice.get(g.kind);
    if (chosen && g.choices.some((c) => c.id === chosen)) return chosen;
    // default: last in payload order (largest, per test) — payload is sorted ascending, last is max
    return g.choices[g.choices.length - 1].id;
  };

  const isSelectedGroup = (g: Group) => {
    if (selectedId === null) return false;
    return g.choices.some((c) => c.id === selectedId);
  };

  return (
    <div className="card" data-testid="decision-block">
      <div className="section-label">Choose one major action</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {groups.map((g) => {
          const selected = isSelectedGroup(g);
          const effId = effectiveId(g);
          const effChoice = g.choices.find((c) => c.id === effId) ?? g.choices[0];
          // When user clicks verb card, select effective choice
          return (
            <div key={g.kind}>
              <button
                className="verb-card"
                data-testid={`verb-${g.kind}`}
                data-selected={selected ? "true" : "false"}
                data-kind={g.kind}
                onClick={() => onSelect(effId)}
              >
                <div className="verb-card-title">{g.kind}</div>
                <div className="verb-card-label">{effChoice.label}</div>
                {effChoice.cost !== null ? (
                  <div className="verb-card-cost num">Cost: {effChoice.cost} coins</div>
                ) : null}
                {/* cost 0 must show — check !== null not truthiness per B6 */}
              </button>
              {g.choices.length > 1 ? (
                <div className="quantity-toggle" data-testid={`qty-toggle-${g.kind}`}>
                  {g.choices.map((c) => {
                    const qty = c.quantity;
                    const active = effId === c.id;
                    return (
                      <button
                        key={c.id}
                        data-testid={`qty-${c.id}`}
                        data-active={active ? "true" : "false"}
                        onClick={() => {
                          setQtyChoice((prev) => {
                            const next = new Map(prev);
                            next.set(g.kind, c.id);
                            return next;
                          });
                          onSelect(c.id);
                        }}
                      >
                        {qty !== null ? String(qty) : c.id}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
      <div className="commit-bar">
        <button
          className="commit-btn"
          data-testid="commit"
          disabled={selectedId === null || committing}
          onClick={onCommit}
        >
          {committing ? "Committing…" : selectedId ? "Commit" : "Select an action"}
        </button>
      </div>
    </div>
  );
}
