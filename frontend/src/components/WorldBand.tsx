export function WorldBand({ signal, pressureStage }: { signal: string; pressureStage: string }) {
  return (
    <div className="world-band" data-testid="world-band" data-pressure-stage={pressureStage}>
      <div className="world-signal">{signal}</div>
      <div className="world-meta">{pressureStage}</div>
    </div>
  );
}
