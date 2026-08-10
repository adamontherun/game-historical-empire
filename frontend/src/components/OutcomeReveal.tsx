import { useEffect, useState } from "react";
import type { GameView } from "../api/types";
import { signedMoney, signedPricePerUnit } from "../lib/format";

export function OutcomeReveal({
  game,
  onContinue,
  onFinish,
}: {
  game: GameView;
  onContinue: () => void;
  onFinish: () => void;
}) {
  const outcome = game.latest_outcome!;
  const isLastTurn = game.completion_summary !== null;
  // staged beats 0..6; reveal reads latest_outcome.* except beat 5 rivals (top-level) and beat 6 signal (top-level) per B5
  const [visibleBeats, setVisibleBeats] = useState(0);
  const [reduced] = useState(() => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);

  useEffect(() => {
    if (reduced) {
      setVisibleBeats(7);
      return;
    }
    let cur = 0;
    const id = setInterval(() => {
      cur += 1;
      setVisibleBeats(cur);
      if (cur >= 7) clearInterval(id);
    }, 260);
    return () => clearInterval(id);
  }, [reduced, outcome.resolved_turn]);

  const complete = visibleBeats >= 7;
  const rival = game.rival_headlines;

  return (
    <div
      className="outcome-reveal"
      data-testid="outcome-reveal"
      data-reveal-state={complete ? "complete" : "revealing"}
    >
      <header data-reveal-beat="0" data-testid="beat-time">
        Turn {outcome.resolved_turn + 1} · {outcome.title}
      </header>

      {visibleBeats >= 1 ? (
        <div className="reveal-beat" data-reveal-beat="1" data-testid="beat-world">
          <div className="beat-label">World</div>
          <div className="beat-value">
            {outcome.world} · {outcome.pressure_stage}
          </div>
        </div>
      ) : null}

      {visibleBeats >= 2 ? (
        <div className="reveal-beat" data-reveal-beat="2" data-testid="beat-numbers">
          <div className="beat-label">Numbers</div>
          <div className="beat-value num">
            Wealth {signedMoney(outcome.wealth_delta)} · Grain {outcome.inventory_delta > 0 ? `+${outcome.inventory_delta}` : String(outcome.inventory_delta)} · Home
            price {signedPricePerUnit(outcome.price_delta)} / grain
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-soft)", marginTop: 4 }}>
            Home price {signedPricePerUnit(outcome.price_delta)} / grain (R6)
          </div>
        </div>
      ) : null}

      {visibleBeats >= 3 ? (
        <div className="reveal-beat" data-reveal-beat="3" data-testid="beat-drivers">
          <div className="beat-label">Top drivers (≤3)</div>
          <div className="driver-list">
            {outcome.drivers.map((d) => {
              const positive = d.impact_money > 0;
              const negative = d.impact_money < 0;
              return (
                <div key={d.id} className="driver-row" data-testid={`driver-${d.id}`}>
                  <span>{d.label}</span>
                  <span className={`impact num ${positive ? "positive" : negative ? "negative" : ""}`}>
                    {signedMoney(d.impact_money)}
                  </span>
                </div>
              );
            })}
            {outcome.drivers.length === 0 ? <div style={{ fontSize: 13 }}>No material drivers</div> : null}
          </div>
          {/* B7: never invent residual; no stacked bar */}
        </div>
      ) : null}

      {visibleBeats >= 4 ? (
        <div className="reveal-beat" data-reveal-beat="4" data-testid="beat-why">
          <div className="beat-label">Why — causal chain</div>
          <details>
            <summary>Show the full chain ({outcome.causal_trace.nodes.length} nodes)</summary>
            <div style={{ marginTop: 8, fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
              {outcome.causal_trace.nodes.map((n) => (
                <div key={n.id} data-testid={`trace-${n.id}`}>
                  <strong>{n.id}</strong>: {n.label} {n.delta !== null ? `Δ ${n.delta}` : ""}
                </div>
              ))}
            </div>
          </details>
        </div>
      ) : null}

      {visibleBeats >= 5 ? (
        <div className="reveal-beat" data-reveal-beat="5" data-testid="beat-rivals">
          <div className="beat-label">Rivals this turn</div>
          {rival ? (
            <>
              <div className="rival-line">Mira: {rival.mira}</div>
              <div className="rival-line">Daran: {rival.daran}</div>
            </>
          ) : (
            <div style={{ fontSize: 13 }}>Mira and Daran acted after your first decision</div>
          )}
        </div>
      ) : null}

      {visibleBeats >= 6 ? (
        <div className="reveal-beat" data-reveal-beat="6" data-testid="beat-next">
          <div className="beat-label">Next threat</div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 16 }}>{game.signal}</div>
          <div style={{ fontSize: 11, color: "var(--ink-soft)" }}>{game.pressure_stage}</div>
        </div>
      ) : null}

      <div style={{ padding: 12, display: "flex", gap: 8 }}>
        {!complete ? (
          <button data-testid="reveal-skip" onClick={() => setVisibleBeats(7)} style={{ padding: "8px 12px" }}>
            Skip
          </button>
        ) : null}
        {complete ? (
          <button
            data-testid={isLastTurn ? "reveal-finish" : "reveal-continue"}
            onClick={isLastTurn ? onFinish : onContinue}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: 10,
              border: 0,
              background: "var(--ink)",
              color: "white",
              fontWeight: 600,
            }}
          >
            {isLastTurn ? "Finish" : "Continue"}
          </button>
        ) : null}
      </div>
    </div>
  );
}
