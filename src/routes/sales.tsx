import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card, Field, PrimaryButton, fieldClass } from "@/components/ui-bits";
import { formatUgx, formatWhen, startOfToday } from "@/lib/format";
import { persistSale } from "@/lib/shop-api";
import { useShop } from "@/lib/store";

export const Route = createFileRoute("/sales")({ component: SalesPage });

function SalesPage() {
  const items = useShop((s) => s.items);
  const sales = useShop((s) => s.sales);
  const recordSale = useShop((s) => s.recordSale);
  const cloud = useShop((s) => s.cloud);
  const subActive = useShop((s) => s.subActive);
  const applyWorkspace = useShop((s) => s.applyWorkspace);
  const canManageStock = useShop((s) => s.canManageStock);
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [price, setPrice] = useState("");

  const selected = items.find((it) => it.id === itemId);
  const todayStart = startOfToday();
  const todaySales = useMemo(
    () => sales.filter((s) => new Date(s.createdAt).getTime() >= todayStart),
    [sales, todayStart],
  );
  const todayTotal = todaySales.reduce((n, s) => n + s.quantity * s.sellPrice, 0);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Sell</h1>
          <p className="mt-1 text-sm text-muted">
            Today you have sold {formatUgx(todayTotal)}
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <Card className="p-5 sm:p-6">
            <h2 className="mb-4 text-lg font-semibold">What did they buy?</h2>
            {!canManageStock ? (
              <p className="text-sm text-muted">You can look, but you cannot record a sale.</p>
            ) : (
            <form
              className="space-y-3"
              onSubmit={async (e) => {
                e.preventDefault();
                if (!subActive) {
                  toast.error("This shop is paused. Pay from Billing to sell again.");
                  return;
                }
                if (!canManageStock) {
                  toast.error("You cannot record sales.");
                  return;
                }
                if (!itemId) {
                  toast.error("Choose a product.");
                  return;
                }
                const payload = {
                  itemId,
                  quantity: Number(quantity) || 0,
                  sellPrice: price === "" ? undefined : Number(price),
                };
                const res = recordSale(payload);
                if (!res.ok) {
                  toast.error(res.error);
                  return;
                }
                if (cloud) {
                  try {
                    applyWorkspace(await persistSale({ data: payload }));
                  } catch (err) {
                    toast.error(err instanceof Error ? err.message : "Saved on this phone only.");
                  }
                }
                toast.success("Sale recorded");
                setQuantity("1");
                setPrice("");
              }}
            >
              <Field label="Product">
                <select
                  required
                  value={itemId}
                  onChange={(e) => {
                    setItemId(e.target.value);
                    const next = items.find((it) => it.id === e.target.value);
                    setPrice(next ? String(next.sellPrice) : "");
                  }}
                  className={fieldClass}
                >
                  <option value="">Choose…</option>
                  {items.map((it) => (
                    <option key={it.id} value={it.id} disabled={it.quantity === 0}>
                      {it.name} · {it.quantity} left
                    </option>
                  ))}
                </select>
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Qty">
                  <input
                    type="number"
                    min={1}
                    max={selected?.quantity ?? undefined}
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className={fieldClass}
                  />
                </Field>
                <Field label="Unit price">
                  <input
                    type="number"
                    min={0}
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className={fieldClass}
                  />
                </Field>
              </div>
              {selected && (
                <p className="text-sm text-muted">
                  Line {formatUgx((Number(quantity) || 0) * (Number(price) || selected.sellPrice))}
                </p>
              )}
              <PrimaryButton type="submit" className="w-full">
                Done
              </PrimaryButton>
            </form>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="border-b border-line px-5 py-4">
              <h2 className="text-lg font-semibold">Recent sales</h2>
            </div>
            <ul className="divide-y divide-line">
              {sales.slice(0, 12).map((sale) => (
                <li key={sale.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {sale.quantity} × {sale.itemName}
                    </p>
                    <p className="text-xs text-muted">{formatWhen(sale.createdAt)}</p>
                  </div>
                  <p className="shrink-0 tabular-nums text-sm">
                    {formatUgx(sale.quantity * sale.sellPrice)}
                  </p>
                </li>
              ))}
              {sales.length === 0 && (
                <li className="px-5 py-12 text-center text-sm text-muted">No sales yet.</li>
              )}
            </ul>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
