import type { GameView } from "../api/types";
import { money, signedMoney } from "../lib/format";
import { formatRunRecord } from "../lib/runRecord";

// R10 hierarchy
export function CompletionSummary({
  game,
  choiceIds,
  onPlayAgain,
}: {
  game: GameView;
  choiceIds: string[];
  onPlayAgain: () => void;
}) {
  const c = game.completion_summary!;
  const positive = c.wealth_delta_total >= 0;
  const runRecord = formatRunRecord(game.run_seed, game.ruleset_version, choiceIds);

  const handleCopy = async () => {
    try {
      const nav = navigator as unknown as { clipboard?: { writeText?: (t: string) => Promise<void> } };
      if (nav.clipboard?.writeText) {
        await nav.clipboard.writeText(runRecord);
        return;
      }
      // fallback: textarea + execCommand
      const ta = document.createElement("textarea");
      ta.value = runRecord;
      ta.setAttribute("readonly", "");
      ta.style.position = "absolute";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const doc = document as unknown as { execCommand?: (cmd: string) => boolean };
      if (doc.execCommand) doc.execCommand("copy");
      document.body.removeChild(ta);
    } catch {
      // swallow — do not throw, do not log (AC7)
    }
  };
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
            Rivals · {c.final_rival_headlines.mira} / {c.final_rival_headlines.daran}
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

      <div
        data-testid="run-record-replay"
        style={{
          marginTop: 12,
          padding: "10px 12px",
          background: "var(--card, #fff)",
          borderRadius: 8,
          border: "1px solid var(--border, #e5e5e5)",
          fontSize: 12,
          wordBreak: "break-all",
          fontFamily: "monospace",
        }}
      >
        {runRecord}
      </div>
      <button
        onClick={handleCopy}
        data-testid="copy-run-record"
        style={{
          marginTop: 8,
          padding: "8px 12px",
          borderRadius: 8,
          border: "1px solid var(--border, #e5e5e5)",
          background: "white",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Copy run record
      </button>

      <div className="footer-debug" data-testid="completion-seed" style={{ marginTop: 12, borderTop: 0 }}>
        seed {game.run_seed} · rules {game.ruleset_version}
      </div>
    </div>
  );
}
