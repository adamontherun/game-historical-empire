/**
 * Unit-conversion boundary — ONLY file allowed to divide by 1000 or 10000.
 * Prices are milliunits (5000 → 5.000), BPS is basis points (4000 → 40%).
 * All other files must import from here; see K2 / B7.
 */

function fmtInt(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

export function money(n: number): string {
  return fmtInt(n);
}

export function signedMoney(n: number): string {
  if (n > 0) return `+${fmtInt(n)}`;
  if (n < 0) return `−${fmtInt(Math.abs(n))}`;
  return "0";
}

export function pricePerUnit(milli: number): string {
  const sign = milli < 0 ? "−" : "";
  const abs = Math.abs(milli);
  const whole = Math.floor(abs / 1000);
  const frac = abs % 1000;
  return `${sign}${whole}.${String(frac).padStart(3, "0")}`;
}

export function signedPricePerUnit(milli: number): string {
  if (milli > 0) return `+${pricePerUnit(milli)}`;
  if (milli < 0) return pricePerUnit(milli);
  return `0.000`;
}

export function percent(bps: number): string {
  if (bps % 100 === 0) return `${bps / 100}%`;
  if (bps % 10 === 0) return `${(bps / 100).toFixed(1)}%`;
  return `${(bps / 100).toFixed(2)}%`;
}
