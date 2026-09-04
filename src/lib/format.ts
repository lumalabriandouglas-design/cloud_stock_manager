export function formatUgx(value: number): string {
  const rounded = Math.round(value);
  return `UGX ${rounded.toLocaleString("en-UG")}`;
}

export function formatQty(value: number): string {
  return value.toLocaleString("en-UG");
}

export function formatWhen(iso: string): string {
  const date = new Date(iso);
  const now = Date.now();
  const diff = now - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString("en-UG", {
    day: "numeric",
    month: "short",
  });
}

export function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("en-UG", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function startOfToday(): number {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function startOfDaysAgo(n: number): number {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - n);
  return d.getTime();
}
