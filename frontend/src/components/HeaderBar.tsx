import { money } from "../lib/format";

const CHAPTER_LABEL = "Age of Grain \u00B7 Chapter I";

export function HeaderBar({
  turn,
  turnLimit,
  cash,
}: {
  turn: number;
  turnLimit: number;
  cash: number;
}) {
  return (
    <div className="header-bar" data-testid="header-bar">
      <div>
        <div className="header-age">{CHAPTER_LABEL}</div>
        <div className="header-turn-label" data-testid="turn-label">
          Turn {turn + 1} of {turnLimit}
        </div>
      </div>
      <div className="header-pips" data-testid="turn-pips" aria-label={`Turn ${turn + 1} of ${turnLimit}`}>
        {Array.from({ length: turnLimit }).map((_, i) => (
          <span key={i} className={i < turn + 1 ? "pip filled" : "pip"} data-testid={i < turn + 1 ? "pip-filled" : "pip-empty"} />
        ))}
      </div>
      <div className="header-cash num" data-testid="header-cash">
        {money(cash)} coins
      </div>
    </div>
  );
}
