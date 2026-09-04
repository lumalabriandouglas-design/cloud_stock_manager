import { useMemo, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card, Field, GhostButton, PrimaryButton, StockPill, fieldClass } from "@/components/ui-bits";
import { formatUgx, startOfToday } from "@/lib/format";
import { persistDeleteItem, persistItem, persistReceive } from "@/lib/shop-api";
import { useShop } from "@/lib/store";
import type { Item } from "@/lib/types";

export function InventoryScreen({
  low,
  onToggleLow,
}: {
  low?: string;
  onToggleLow: () => void;
}) {
  const items = useShop((s) => s.items);
  const sales = useShop((s) => s.sales);
  const categories = useShop((s) => s.categories);
  const receiveStock = useShop((s) => s.receiveStock);
  const upsertItem = useShop((s) => s.upsertItem);
  const addCategory = useShop((s) => s.addCategory);
  const deleteItem = useShop((s) => s.deleteItem);
  const cloud = useShop((s) => s.cloud);
  const subActive = useShop((s) => s.subActive);
  const applyWorkspace = useShop((s) => s.applyWorkspace);
  const canManageStock = useShop((s) => s.canManageStock);
  const canEditItems = useShop((s) => s.canEditItems);
  const canManageCategories = useShop((s) => s.canManageCategories);

  const [query, setQuery] = useState("");
  const [cat, setCat] = useState("");
  const [shown, setShown] = useState(40);
  const [editing, setEditing] = useState<Item | "new" | "receive" | null>(
    null,
  );

  const overview = useMemo(() => {
    const start = startOfToday();
    const todayTotal = sales
      .filter((sale) => new Date(sale.createdAt).getTime() >= start)
      .reduce((n, sale) => n + sale.quantity * sale.sellPrice, 0);
    const lowItems = items.filter((it) => it.quantity <= it.reorderLevel);
    return {
      productCount: items.length,
      inventoryValue: items.reduce((n, it) => n + it.quantity * it.buyPrice, 0),
      lowCount: lowItems.length,
      lowItems,
      todayTotal,
    };
  }, [items, sales]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items
      .filter((it) => (low === "1" ? it.quantity <= it.reorderLevel : true))
      .filter((it) => (cat ? it.categoryId === cat : true))
      .filter((it) => (q ? it.name.toLowerCase().includes(q) : true))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [items, query, cat, low]);

  const grouped = useMemo(() => {
    const visible = filtered.slice(0, shown);
    const order: { id: string; name: string; items: Item[] }[] = [];
    const index = new Map<string, number>();
    for (const item of visible) {
      const id = item.categoryId ?? "_none";
      const name = categories.find((c) => c.id === item.categoryId)?.name ?? "No category";
      const existing = index.get(id);
      if (existing === undefined) {
        index.set(id, order.length);
        order.push({ id, name, items: [item] });
      } else {
        order[existing].items.push(item);
      }
    }
    return order;
  }, [filtered, shown, categories]);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Inventory</h1>
            <p className="mt-1 text-sm text-muted">What you have, and what to buy again.</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Products" value={String(overview.productCount)} />
          <Stat label="Stock worth" value={formatUgx(overview.inventoryValue)} />
          <button
            type="button"
            onClick={onToggleLow}
            className="rounded-lg bg-surface p-3 text-left shadow-card sm:p-4"
          >
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Low stock</p>
            <p className={`mt-1 font-serif text-xl font-semibold tabular-nums ${overview.lowCount ? "text-accent" : ""}`}>
              {overview.lowCount}
            </p>
          </button>
          <Stat label="Sold today" value={formatUgx(overview.todayTotal)} />
        </div>

        {overview.lowItems.length > 0 && (
          <Card className="bg-warn-bg p-4 sm:p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-warn">Needs restocking</h2>
              <button type="button" onClick={onToggleLow} className="text-xs text-warn hover:underline">
                {low === "1" ? "Show all" : "View in list"}
              </button>
            </div>
            <ul className="space-y-2">
              {overview.lowItems.slice(0, 8).map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="min-w-0 truncate font-medium">{item.name}</span>
                  <span className="flex shrink-0 items-center gap-3">
                    <span className="text-xs text-warn">
                      {item.quantity} left{" "}
                      <span className="text-muted">(reorder at {item.reorderLevel})</span>
                    </span>
                    <button
                      type="button"
                      className="text-xs text-muted hover:text-primary"
                      onClick={() => canEditItems && setEditing(item)}
                    >
                      {canEditItems ? "Edit" : ""}
                    </button>
                  </span>
                </li>
              ))}
            </ul>
            {overview.lowItems.length > 8 && (
              <p className="mt-2 text-xs text-muted">+{overview.lowItems.length - 8} more. Use Low stock to see them.</p>
            )}
          </Card>
        )}

        {canManageStock && (
        <Card className="overflow-hidden">
          <div className="border-b border-line px-4 py-3 sm:px-5">
            <h2 className="text-sm font-semibold">Add stock</h2>
            <p className="mt-0.5 text-xs text-muted">
              Type a product you already sell, or a new name. A new name is created and counted in one step.
            </p>
          </div>
          <div className="p-4 sm:p-5">
            <ReceiveForm
              items={items}
              categories={categories}
              onAddCategory={addCategory}
              canManageCategories={canManageCategories}
              onSubmit={async (payload) => {
                if (!subActive) {
                  toast.error("This shop is paused.");
                  return false;
                }
                const existed = items.some(
                  (it) =>
                    it.id === payload.itemId ||
                    it.name.toLowerCase() === payload.name.trim().toLowerCase(),
                );
                const res = receiveStock(payload);
                if (!res.ok) {
                  toast.error(res.error);
                  return false;
                }
                if (cloud) {
                  try {
                    applyWorkspace(await persistReceive({ data: payload }));
                  } catch (err) {
                    toast.error(err instanceof Error ? err.message : "Saved on this phone only.");
                  }
                }
                toast.success(existed ? "Stock added" : "New product added to inventory");
                return true;
              }}
            />
          </div>
        </Card>
        )}

        <Card className="overflow-hidden">
          <div className="space-y-3 border-b border-line px-4 py-3 sm:px-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Inventory</h2>
              <span className="text-xs text-muted">
                {filtered.length} shown
                {filtered.length !== items.length ? ` of ${items.length}` : ""}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setShown(40);
                }}
                placeholder="Search products…"
                className={`${fieldClass} h-10 min-w-40 flex-1`}
              />
              <select
                value={cat}
                onChange={(e) => {
                  setCat(e.target.value);
                  setShown(40);
                }}
                className={`${fieldClass} h-10 w-auto min-w-36`}
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-md px-3 text-sm shadow-card">
                <input type="checkbox" checked={low === "1"} onChange={onToggleLow} />
                Low stock
              </label>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted">
                  <th className="px-4 py-2.5 font-medium sm:px-5">Product</th>
                  <th className="hidden px-4 py-2.5 font-medium sm:table-cell sm:px-5">Category</th>
                  <th className="px-4 py-2.5 font-medium sm:px-5">Buy</th>
                  <th className="px-4 py-2.5 font-medium sm:px-5">Sell</th>
                  <th className="px-4 py-2.5 font-medium sm:px-5">Stock</th>
                  <th className="px-4 py-2.5 font-medium sm:px-5" />
                </tr>
              </thead>
              <tbody>
                {grouped.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-12 text-center text-sm text-muted">
                      No products match.
                    </td>
                  </tr>
                )}
                {grouped.map((group) => (
                  <CategoryBlock
                    key={group.id}
                    name={group.name}
                    items={group.items}
                    hideHeading={Boolean(cat) || grouped.length === 1}
                    onEdit={canEditItems ? setEditing : undefined}
                  />
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length > shown && (
            <div className="border-t border-line px-4 py-3 text-center sm:px-5">
              <button
                type="button"
                className="text-sm font-medium text-primary"
                onClick={() => setShown((n) => n + 40)}
              >
                Show more ({filtered.length - shown} left)
              </button>
            </div>
          )}
        </Card>
      </div>

      {editing && editing !== "receive" && editing !== "new" && (
        <Sheet title="Edit product" onClose={() => setEditing(null)}>
          <ItemForm
            item={editing}
            categories={categories}
            onAddCategory={addCategory}
            onDelete={async () => {
              deleteItem(editing.id);
              if (cloud) {
                try {
                  applyWorkspace(await persistDeleteItem({ data: editing.id }));
                } catch {
                  /* local already removed */
                }
              }
              toast.success("Removed");
              setEditing(null);
            }}
            onSubmit={async (payload) => {
              const res = upsertItem(payload);
              if (!res.ok) {
                toast.error(res.error);
                return;
              }
              if (cloud) {
                try {
                  applyWorkspace(await persistItem({ data: payload }));
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Saved on this phone only.");
                }
              }
              toast.success("Saved");
              setEditing(null);
            }}
          />
        </Sheet>
      )}
    </AppShell>
  );
}

function Sheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <button type="button" className="absolute inset-0 bg-ink/30" aria-label="Close" onClick={onClose} />
      <div className="relative max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-t-lg bg-surface p-5 shadow-card sm:rounded-lg sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">{title}</h2>
          <GhostButton className="h-9" onClick={onClose}>
            Close
          </GhostButton>
        </div>
        {children}
      </div>
    </div>
  );
}

function ItemForm({
  item,
  categories,
  onAddCategory,
  onSubmit,
  onDelete,
}: {
  item: Item | null;
  categories: { id: string; name: string }[];
  onAddCategory: (name: string) => string | null;
  onSubmit: (payload: {
    id?: string;
    name: string;
    categoryId: string | null;
    buyPrice: number;
    sellPrice: number;
    quantity?: number;
    reorderLevel: number;
  }) => void;
  onDelete?: () => void;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [categoryId, setCategoryId] = useState(item?.categoryId ?? "");
  const [buyPrice, setBuyPrice] = useState(String(item?.buyPrice ?? ""));
  const [sellPrice, setSellPrice] = useState(String(item?.sellPrice ?? ""));
  const [quantity, setQuantity] = useState(String(item?.quantity ?? "0"));
  const [reorderLevel, setReorderLevel] = useState(String(item?.reorderLevel ?? "5"));
  const [newCat, setNewCat] = useState("");

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          id: item?.id,
          name,
          categoryId: categoryId || null,
          buyPrice: Number(buyPrice) || 0,
          sellPrice: Number(sellPrice) || 0,
          quantity: Number(quantity) || 0,
          reorderLevel: Number(reorderLevel) || 0,
        });
      }}
    >
      <Field label="Name">
        <input required value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="Category">
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className={fieldClass}>
          <option value="">None</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <div className="flex gap-2">
        <input
          value={newCat}
          onChange={(e) => setNewCat(e.target.value)}
          placeholder="New category"
          className={fieldClass}
        />
        <GhostButton
          type="button"
          onClick={() => {
            const id = onAddCategory(newCat);
            if (id) {
              setCategoryId(id);
              setNewCat("");
            }
          }}
        >
          Add
        </GhostButton>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Buy (UGX)">
          <input type="number" min={0} value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="Sell (UGX)">
          <input type="number" min={0} value={sellPrice} onChange={(e) => setSellPrice(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="Quantity">
          <input type="number" min={0} value={quantity} onChange={(e) => setQuantity(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="Reorder at">
          <input type="number" min={0} value={reorderLevel} onChange={(e) => setReorderLevel(e.target.value)} className={fieldClass} />
        </Field>
      </div>
      <PrimaryButton type="submit" className="w-full">
        Save
      </PrimaryButton>
      {onDelete && (
        <GhostButton type="button" className="w-full text-danger" onClick={onDelete}>
          Remove product
        </GhostButton>
      )}
    </form>
  );
}

function ReceiveForm({
  items,
  categories,
  onAddCategory,
  onSubmit,
  canManageCategories,
}: {
  items: Item[];
  categories: { id: string; name: string }[];
  onAddCategory: (name: string) => string | null;
  canManageCategories?: boolean;
  onSubmit: (payload: {
    itemId?: string;
    name: string;
    quantity: number;
    buyPrice?: number;
    sellPrice?: number;
    categoryId?: string | null;
  }) => void | boolean | Promise<void | boolean>;
}) {
  const [name, setName] = useState("");
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [buyPrice, setBuyPrice] = useState("");
  const [sellPrice, setSellPrice] = useState("");
  const [categoryId, setCategoryId] = useState("");

  const match = items.find((it) => it.name.toLowerCase() === name.trim().toLowerCase());

  return (
    <form
      className="space-y-3"
      onSubmit={async (e) => {
        e.preventDefault();
        const ok = await onSubmit({
          itemId: match?.id ?? itemId ?? undefined,
          name,
          quantity: Number(quantity) || 0,
          buyPrice: buyPrice === "" ? undefined : Number(buyPrice),
          sellPrice: sellPrice === "" ? undefined : Number(sellPrice),
          categoryId: categoryId || null,
        });
        if (ok === false) return;
        setName("");
        setItemId("");
        setQuantity("1");
        setBuyPrice("");
        setSellPrice("");
        setCategoryId("");
      }}
    >
      <Field label="Product">
        <input
          list="stock-items"
          required
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            const found = items.find((it) => it.name.toLowerCase() === e.target.value.toLowerCase());
            setItemId(found?.id ?? "");
            if (found) {
              setBuyPrice(String(found.buyPrice));
              setSellPrice(String(found.sellPrice));
              setCategoryId(found.categoryId ?? "");
            }
          }}
          placeholder="Name or pick one you already have"
          className={fieldClass}
        />
        <datalist id="stock-items">
          {items.map((it) => (
            <option key={it.id} value={it.name} />
          ))}
        </datalist>
        {name.trim() ? (
          <p className="mt-1.5 text-xs text-muted">
            {match
              ? `Already in inventory · ${match.quantity} on the shelf. This adds more.`
              : "New product. It will be added to inventory with this quantity."}
          </p>
        ) : null}
      </Field>
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <Field label="Qty">
          <input type="number" min={1} required value={quantity} onChange={(e) => setQuantity(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="Buy">
          <input type="number" min={0} value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} className={fieldClass} placeholder="0" />
        </Field>
        <Field label="Sell">
          <input type="number" min={0} value={sellPrice} onChange={(e) => setSellPrice(e.target.value)} className={fieldClass} placeholder="0" />
        </Field>
      </div>
      <Field label="Category">
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className={fieldClass}>
          <option value="">—</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      {canManageCategories && (
        <GhostButton
          type="button"
          onClick={() => {
            const label = window.prompt("Category name");
            if (label) {
              const id = onAddCategory(label);
              if (id) setCategoryId(id);
            }
          }}
        >
          New category
        </GhostButton>
      )}
      <PrimaryButton type="submit" className="w-full">
        {match ? "Add to shelf" : "Add new product"}
      </PrimaryButton>
    </form>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface p-3 shadow-card sm:p-4">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-serif text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function money(value: number) {
  return value.toLocaleString("en-UG");
}

function CategoryBlock({
  name,
  items,
  hideHeading,
  onEdit,
}: {
  name: string;
  items: Item[];
  hideHeading: boolean;
  onEdit?: (item: Item) => void;
}) {
  return (
    <>
      {!hideHeading && (
        <tr className="bg-bg">
          <td colSpan={6} className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted sm:px-5">
            {name}
            <span className="ml-2 font-normal normal-case">{items.length}</span>
          </td>
        </tr>
      )}
      {items.map((item) => (
        <tr key={item.id} className="border-t border-line/70">
          <td className="px-4 py-2.5 font-medium sm:px-5">
            <p className="truncate">{item.name}</p>
            <p className="text-xs text-muted sm:hidden">{name}</p>
          </td>
          <td className="hidden px-4 py-2.5 text-muted sm:table-cell sm:px-5">{name}</td>
          <td className="px-4 py-2.5 font-mono text-xs tabular-nums text-muted sm:px-5">{money(item.buyPrice)}</td>
          <td className="px-4 py-2.5 font-mono text-xs tabular-nums sm:px-5">{money(item.sellPrice)}</td>
          <td className="px-4 py-2.5 sm:px-5">
            <StockPill qty={item.quantity} reorder={item.reorderLevel} />
          </td>
          <td className="px-4 py-2.5 text-right sm:px-5">
            {onEdit && (
              <button type="button" className="text-xs text-muted hover:text-primary" onClick={() => onEdit(item)}>
                Edit
              </button>
            )}
          </td>
        </tr>
      ))}
    </>
  );
}

