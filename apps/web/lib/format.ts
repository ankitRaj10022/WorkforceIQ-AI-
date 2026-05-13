export function formatCurrency(value: number | null | undefined) {
  if (value == null) {
    return "N/A";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "N/A";
  }
  return `${Math.round(value * 100)}%`;
}

export function toTitleCase(value: string) {
  return value
    .toLowerCase()
    .split(/[_\s-]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
