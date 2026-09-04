import { Link } from "@tanstack/react-router";
import { ChartNoAxesCombined, CreditCard, Download, House, Settings2, Shield, Upload, Users } from "lucide-react";
import { useShop } from "@/lib/store";
import { persistReceive } from "@/lib/shop-api";
import { cn } from "@/lib/cn";
import { useRef, useState } from "react";
import { toast } from "sonner";

export function SettingsMenu() {
  const [open, setOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const canViewReports = useShop((s) => s.canViewReports);
  const canManageStock = useShop((s) => s.canManageStock);
  const canManageTeam = useShop((s) => s.canManageTeam);
  const isOwner = useShop((s) => s.isOwner);
  const isPlatformAdmin = useShop((s) => s.isPlatformAdmin);
  const cloud = useShop((s) => s.cloud);
  const items = useShop((s) => s.items);
  const sales = useShop((s) => s.sales);
  const categories = useShop((s) => s.categories);
  const receiveStock = useShop((s) => s.receiveStock);
  const applyWorkspace = useShop((s) => s.applyWorkspace);

  function exportCsv(kind: "stock" | "sales") {
    const rows =
      kind === "stock"
        ? [
            ["Name", "Category", "Buy", "Sell", "Qty", "Reorder"],
            ...items.map((it) => [
              it.name,
              categories.find((c) => c.id === it.categoryId)?.name ?? "",
              it.buyPrice,
              it.sellPrice,
              it.quantity,
              it.reorderLevel,
            ]),
          ]
        : [
            ["When", "Product", "Qty", "Unit", "Total", "Profit"],
            ...sales.map((s) => [
              s.createdAt,
              s.itemName,
              s.quantity,
              s.sellPrice,
              s.quantity * s.sellPrice,
              s.quantity * (s.sellPrice - s.costPrice),
            ]),
          ];
    const csv = rows.map((r) => r.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${kind}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setOpen(false);
  }

  async function onImport(file: File) {
    const text = await file.text();
    const lines = text.split(/\r?\n/).filter((l) => l.trim());
    if (lines.length < 2) {
      toast.error("The file looks empty.");
      return;
    }
    const body = lines.slice(1);
    let added = 0;
    for (const line of body) {
      const cols = line.split(",").map((c) => c.replace(/^"|"$/g, "").trim());
      const name = cols[0];
      const qty = Number(cols[4] ?? cols[1]) || 0;
      if (!name || qty < 1) continue;
      const buy = Number(cols[2] ?? 0) || 0;
      const sell = Number(cols[3] ?? 0) || 0;
      receiveStock({ name, quantity: qty, buyPrice: buy, sellPrice: sell });
      if (cloud) {
        try {
          const ws = await persistReceive({
            data: { name, quantity: qty, buyPrice: buy, sellPrice: sell },
          });
          applyWorkspace(ws);
        } catch {
          /* local copy already applied */
        }
      }
      added += 1;
    }
    toast.success(added ? `Added ${added} rows` : "No rows could be read");
    setOpen(false);
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="More"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="grid size-10 place-items-center rounded-md text-muted hover:bg-surface hover:text-ink"
      >
        <Settings2 className="size-5" />
      </button>
      {open && (
        <>
          <button type="button" className="fixed inset-0 z-40" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-1 w-56 rounded-md bg-surface py-1 shadow-card">
            <Item to="/today" icon={House} onClick={() => setOpen(false)}>
              Today's numbers
            </Item>
            {canViewReports && (
              <Item to="/reports" icon={ChartNoAxesCombined} onClick={() => setOpen(false)}>
                Sales report
              </Item>
            )}
            {canViewReports && (
              <button type="button" className={rowClass} onClick={() => exportCsv("stock")}>
                <Download className="size-4" /> Export stock
              </button>
            )}
            {canViewReports && (
              <button type="button" className={rowClass} onClick={() => exportCsv("sales")}>
                <Download className="size-4" /> Export sales
              </button>
            )}
            {canManageStock && (
              <button type="button" className={rowClass} onClick={() => fileRef.current?.click()}>
                <Upload className="size-4" /> Import CSV
              </button>
            )}
            {canManageTeam && (
              <Item to="/team" icon={Users} onClick={() => setOpen(false)}>
                Staff & access
              </Item>
            )}
            {isOwner && (
              <Item to="/billing" icon={CreditCard} onClick={() => setOpen(false)}>
                Billing
              </Item>
            )}
            {isPlatformAdmin && (
              <Item to="/platform" icon={Shield} onClick={() => setOpen(false)}>
                Platform admin
              </Item>
            )}
          </div>
        </>
      )}
      <input
        ref={fileRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) void onImport(file);
        }}
      />
    </div>
  );
}

const rowClass =
  "flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm text-ink hover:bg-bg";

function Item({
  to,
  icon: Icon,
  onClick,
  children,
}: {
  to: string;
  icon: typeof Users;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Link to={to} onClick={onClick} className={cn(rowClass)}>
      <Icon className="size-4" />
      {children}
    </Link>
  );
}
