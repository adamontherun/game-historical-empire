// R12: seed · rules
export function FooterDebug({ seed, rules }: { seed: string; rules: string }) {
  return (
    <div className="footer-debug" data-testid="footer-debug">
      seed {seed} · rules {rules}
    </div>
  );
}
