const CHAPTER_LABEL = "Age of Grain \u00B7 Chapter I"; // R9 — presentation constant

export function StartScreen({ onBegin, seed }: { onBegin: () => void; seed?: string }) {
  return (
    <div className="start-screen" data-testid="start-screen">
      <div className="start-label">{CHAPTER_LABEL}</div>
      <div className="start-title">Historical Empire</div>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 15, color: "var(--ink-soft)" }}>
        A five-turn ledger of grain, storage, and river trade.
      </div>
      {seed ? (
        <div style={{ fontSize: 11, color: "var(--ink-soft)" }} data-testid="start-seed">
          seed {seed} · rules 1.0
        </div>
      ) : null}
      <button className="start-btn" onClick={onBegin} data-testid="begin-btn">
        Begin
      </button>
    </div>
  );
}
