import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card, GhostButton, PrimaryButton } from "@/components/ui-bits";
import { formatUgx } from "@/lib/format";
import { PLAN_AMOUNT_UGX } from "@/lib/billing";
import {
  listPlatformCompanies,
  platformAct,
  type PlatformCompany,
} from "@/lib/shop-api";
import { useShop } from "@/lib/store";

export const Route = createFileRoute("/platform")({ component: PlatformPage });

function PlatformPage() {
  const isPlatformAdmin = useShop((s) => s.isPlatformAdmin);
  const [rows, setRows] = useState<PlatformCompany[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPlatformCompanies()
      .then(setRows)
      .catch((err) => setError(err instanceof Error ? err.message : "No access"));
  }, []);

  async function act(companyId: string, action: "activate" | "suspend" | "extend" | "delete") {
    try {
      const next = await platformAct({ data: { companyId, action } });
      setRows(next);
      toast.success("Updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Platform</h1>
          <p className="mt-1 text-sm text-muted">
            Shops pay {formatUgx(PLAN_AMOUNT_UGX)} / month. Grant, pause, or remove access here.
          </p>
        </div>
        {(!isPlatformAdmin || error) && (
          <p className="text-sm text-danger">{error ?? "This page is only for the site owner."}</p>
        )}
        {isPlatformAdmin && (
          <Card className="overflow-hidden">
            <ul className="divide-y divide-line">
              {rows.map((row) => (
                <li key={row.id} className="space-y-3 px-4 py-4 sm:px-5">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{row.name}</p>
                      <p className="text-xs text-muted">{row.ownerEmail || "No email"}</p>
                    </div>
                    <span className={`text-sm font-medium ${row.active ? "text-primary" : "text-danger"}`}>
                      {row.status}
                      {!row.active ? " · closed" : ""}
                    </span>
                  </div>
                  <p className="text-xs text-muted">
                    {row.paymentPhone && `Paid from ${row.paymentPhone}. `}
                    {row.paymentTxId && `Tx ${row.paymentTxId}. `}
                    {row.currentPeriodEnd && `Until ${new Date(row.currentPeriodEnd).toLocaleDateString("en-UG")}.`}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <PrimaryButton className="h-9 px-3 text-xs" onClick={() => act(row.id, "activate")}>
                      Grant 30 days
                    </PrimaryButton>
                    <GhostButton className="h-9" onClick={() => act(row.id, "extend")}>
                      Extend
                    </GhostButton>
                    <GhostButton className="h-9" onClick={() => act(row.id, "suspend")}>
                      Suspend
                    </GhostButton>
                    <GhostButton className="h-9 text-danger" onClick={() => act(row.id, "delete")}>
                      Delete shop
                    </GhostButton>
                  </div>
                </li>
              ))}
              {rows.length === 0 && !error && (
                <li className="px-5 py-10 text-center text-sm text-muted">No shops yet.</li>
              )}
            </ul>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
