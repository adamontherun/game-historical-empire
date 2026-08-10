import type { GameView } from "../api/types";
import { money, signedMoney } from "../lib/format";

// R10 hierarchy
export function CompletionSummary({ game, onPlayAgain }: { game: GameView; onPlayAgain: () => void }) {
  const c = game.completion_summary!;
  const positive = c.wealth_delta_total >= 0;
  return (
    <div className="completion-summary" data-testid="completion-summary">
      <div className="completion-hero">Your five-turn ledger</div>
      <div className="completion-wealth num" data-testid="final-wealth">
        Final wealth {money(c.final_wealth)}
      </div>
      <div className={`completion-delta num ${positive ? "positive" : "negative"}`} data-testid="wealth-delta-total">
        Total change {signedMoney(c.wealth_delta_total)}
      </div>

      <div className="completion-meta">
        <div data-testid="final-estate">
          Final estate · Farm {c.final_farm_capacity} · Storage {c.final_storage_capacity} ·{" "}
          {game.empire_summary.route_established ? "River secured" : "River closed"}
        </div>
        <div data-testid="run-record">
          Run record · Cash low {money(c.cash_low)} · Peak grain {c.peak_inventory}
        </div>
        <div data-testid="final-cash">Cash {money(c.final_cash)}</div>
        <div data-testid="final-grain">Grain {c.final_grain}</div>
        {c.final_rival_headlines ? (
          <div data-testid="final-rivals">
            Rivals · Mira: {c.final_rival_headlines.mira} / Daran: {c.final_rival_headlines.daran}
          </div>
        ) : null}
      </div>

      <button
        onClick={onPlayAgain}
        data-testid="play-again"
        style={{
          marginTop: 16,
          width: "100%",
          padding: "12px 16px",
          borderRadius: 10,
          border: 0,
          background: "var(--ink)",
          color: "white",
          fontWeight: 600,
        }}
      >
        Play again
      </button>

      <div className="footer-debug" data-testid="completion-seed" style={{ marginTop: 12, borderTop: 0 }}>
        seed {game.run_seed} · rules {game.ruleset_version}
      </div>
    </div>
  );
}
