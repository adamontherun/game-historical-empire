import type { RivalHeadlines } from "../api/types";

export function RivalsStrip({ headlines }: { headlines: RivalHeadlines | null }) {
  if (headlines === null) {
    return (
      <div className="card rivals-strip" data-testid="rivals-strip">
        <div className="section-label">Rivals</div>
        <div className="rival-line" data-testid="rivals-empty">
          Mira and Daran act after your first decision
        </div>
      </div>
    );
  }
  return (
    <div className="card rivals-strip" data-testid="rivals-strip">
      <div className="section-label">Rivals</div>
      <div className="rival-line" data-testid="rival-mira">
        Mira: {headlines.mira}
      </div>
      <div className="rival-line" data-testid="rival-daran" style={{ marginTop: 6 }}>
        Daran: {headlines.daran}
      </div>
    </div>
  );
}
