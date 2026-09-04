import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui-bits";
import { formatUgx, startOfDaysAgo } from "@/lib/format";
import { useShop } from "@/lib/store";

export const Route = createFileRoute("/reports")({ component: ReportsPage });

const RANGES = [
  { id: "7", label: "7 days", days: 6 },
  { id: "30", label: "30 days", days: 29 },
  { id: "180", label: "6 months", days: 179 },
  { id: "all", label: "All time", days: 4000 },
] as const;

function ReportsPage() {
  const sales = useShop((s) => s.sales);
  const canViewReports = useShop((s) => s.canViewReports);
  const [range, setRange] = useState<(typeof RANGES)[number]["id"]>("7");
  const spec = RANGES.find((r) => r.id === range) ?? RANGES[0];
  const from = startOfDaysAgo(spec.days);

  const stats = useMemo(() => {
    const rows = sales.filter((s) => new Date(s.createdAt).getTime() >= from);
    const revenue = rows.reduce((n, s) => n + s.quantity * s.sellPrice, 0);
    const profit = rows.reduce((n, s) => n + s.quantity * (s.sellPrice - s.costPrice), 0);
    const units = rows.reduce((n, s) => n + s.quantity, 0);
    const bucketCount = spec.id === "7" ? 7 : spec.id === "30" ? 10 : spec.id === "180" ? 6 : 8;
    const span = spec.days + 1;
    const buckets = Array.from({ length: bucketCount }, (_, i) => {
      const start = startOfDaysAgo(Math.round(((bucketCount - 1 - i) * span) / bucketCount));
      const end = startOfDaysAgo(Math.round(((bucketCount - 2 - i) * span) / bucketCount) - 1);
      const labelDate = new Date(start);
      return {
        label:
          spec.id === "7"
            ? labelDate.toLocaleDateString("en-UG", { weekday: "short" })
            : labelDate.toLocaleDateString("en-UG", { day: "numeric", month: "short" }),
        revenue: rows
          .filter((s) => {
            const t = new Date(s.createdAt).getTime();
            return t >= start && t < end;
          })
          .reduce((n, s) => n + s.quantity * s.sellPrice, 0),
      };
    });
    return { revenue, profit, units, buckets, count: rows.length };
  }, [sales, from, spec]);

  if (!canViewReports) {
    return (
      <AppShell>
        <p className="text-sm text-muted">You cannot open reports. Ask the shop owner.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Sales report</h1>
          <p className="mt-1 text-sm text-muted">Pick a period. Numbers stay simple.</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {RANGES.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setRange(r.id)}
              className={`h-10 rounded-md px-3 text-sm ${range === r.id ? "bg-primary text-primary-fg" : "shadow-card text-muted"}`}
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Mini label="Sold" value={formatUgx(stats.revenue)} />
          <Mini label="Profit" value={formatUgx(stats.profit)} />
          <Mini label="Items sold" value={String(stats.units)} />
        </div>

        <Card className="p-5 sm:p-6">
          <h2 className="mb-4 text-lg font-semibold">{spec.label}</h2>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.buckets} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
                <XAxis dataKey="label" tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: "color-mix(in oklab, var(--color-primary) 8%, transparent)" }}
                  formatter={(v: number) => formatUgx(v)}
                  contentStyle={{
                    border: "none",
                    borderRadius: 10,
                    background: "var(--color-surface)",
                    color: "var(--color-ink)",
                  }}
                />
                <Bar dataKey="revenue" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface p-4 shadow-card">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 font-serif text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
