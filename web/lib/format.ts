// Small currency/percent/ms formatters — no library needed (Intl is stdlib).
export function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 4 }).format(
    value
  );
}

export function formatMs(value: number): string {
  return `${Math.round(value)} ms`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
