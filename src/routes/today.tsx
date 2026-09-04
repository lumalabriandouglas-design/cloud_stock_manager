import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo } from "react";
import { AppShell } from "@/components/app-shell";
import { Card, StockPill } from "@/components/ui-bits";
import { formatUgx, formatWhen, startOfDaysAgo, startOfToday } from "@/lib/format";
import { useShop } from "@/lib/store";

export const Route = createFileRoute("/today")({ component: Today });

function Today() {
  const items = useShop((s) => s.items);
  const sales = useShop((s) => s.sales);
  const activity = useShop((s) => s.activity);
  const categories = useShop((s) => s.categories);

  const stats = useMemo(() => {
    const start = startOfToday();
    const week = startOfDaysAgo(6);
    const todaySales = sales.filter((sale) => new Date(sale.createdAt).getTime() >= start);
    const weekSales = sales.filter((sale) => new Date(sale.createdAt).getTime() >= week);
    const todayTotal = todaySales.reduce((n, sale) => n + sale.quantity * sale.sellPrice, 0);
    const weekTotal = weekSales.reduce((n, sale) => n + sale.quantity * sale.sellPrice, 0);
    const inventoryValue = items.reduce((n, it) => n + it.quantity * it.buyPrice, 0);
    const lowItems = items.filter((it) => it.quantity <= it.reorderLevel);
    return {
      productCount: items.length,
      lowCount: lowItems.length,
      lowItems,
      todayTotal,
      weekTotal,
      inventoryValue,
    };
  }, [items, sales]);

  return (
    <AppShell>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Today</h1>
          <p className="mt-1 text-sm text-muted">See what sold, and what is running out.</p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
          <Stat label="Products" value={String(stats.productCount)} />
          <Stat label="Stock worth" value={formatUgx(stats.inventoryValue)} />
          <Stat
            label="Running low"
            value={String(stats.lowCount)}
            tone={stats.lowCount ? "warn" : undefined}
          />
          <Stat label="Sold today" value={formatUgx(stats.todayTotal)} />
        </div>

        <Card className="p-5 sm:p-6">
          <div className="mb-4 flex items-baseline justify-between gap-3">
            <h2 className="text-lg font-semibold">Running low</h2>
            <Link to="/" search={{ low: "1" }} className="text-sm text-primary hover:underline">
              See inventory
            </Link>
          </div>
          {stats.lowItems.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">Nothing is low. You are fine.</p>
          ) : (
            <ul className="divide-y divide-line">
              {stats.lowItems.map((item) => {
                const cat = categories.find((c) => c.id === item.categoryId)?.name;
                return (
                  <li key={item.id} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.name}</p>
                      <p className="text-xs text-muted">
                        {cat ?? "No group"} · buy more at {item.reorderLevel}
                      </p>
                    </div>
                    <StockPill qty={item.quantity} reorder={item.reorderLevel} />
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card className="p-5 sm:p-6">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-lg font-semibold">This week</h2>
            <Link to="/reports" className="text-sm text-primary hover:underline">
              More numbers
            </Link>
          </div>
          <p className="font-serif text-2xl font-semibold tabular-nums">{formatUgx(stats.weekTotal)}</p>
          <p className="mt-1 text-sm text-muted">Money from sales in the last 7 days.</p>
        </Card>

        <Card className="p-5 sm:p-6">
          <h2 className="mb-4 text-lg font-semibold">Just now</h2>
          {activity.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">Nothing recorded yet.</p>
          ) : (
            <ul className="space-y-3">
              {activity.slice(0, 5).map((a) => (
                <li key={a.id} className="flex items-start justify-between gap-3 text-sm">
                  <span className="min-w-0 leading-snug">{a.message}</span>
                  <span className="shrink-0 text-xs text-muted">{formatWhen(a.createdAt)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "warn";
}) {
  return (
    <div className="rounded-lg bg-surface p-4 shadow-card sm:p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 font-serif text-xl font-semibold tabular-nums sm:text-2xl ${tone === "warn" ? "text-accent" : ""}`}>
        {value}
      </p>
    </div>
  );
}
