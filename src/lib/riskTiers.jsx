export const TIER_HEX = {
  low: "#10b981",
  moderate: "#f59e0b",
  high: "#e11d48",
};

export const TIER_ORDER = { low: 0, moderate: 1, high: 2 };

export function sortByRiskDesc(a, b) {
  return (TIER_ORDER[b.risk_tier] ?? 0) - (TIER_ORDER[a.risk_tier] ?? 0);
}