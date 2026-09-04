import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card, Field, PrimaryButton, fieldClass } from "@/components/ui-bits";
import { PAY_AIRTEL, PAY_MTN, PLAN_AMOUNT_UGX } from "@/lib/billing";
import { formatUgx } from "@/lib/format";
import { claimPayment, loadWorkspace, type Subscription } from "@/lib/shop-api";
import { useShop } from "@/lib/store";

export const Route = createFileRoute("/billing")({ component: BillingPage });

function BillingPage() {
  const applyWorkspace = useShop((s) => s.applyWorkspace);
  const company = useShop((s) => s.companyName);
  const isOwner = useShop((s) => s.isOwner);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [phone, setPhone] = useState("");
  const [txId, setTxId] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    loadWorkspace()
      .then((ws) => {
        applyWorkspace(ws);
        setSub(ws.subscription);
      })
      .catch((err) => toast.error(err instanceof Error ? err.message : "Sign in first."));
  }, [applyWorkspace]);

  return (
    <AppShell>
      <div className="mx-auto max-w-lg space-y-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Billing</h1>
          <p className="mt-1 text-sm text-muted">{company} · {formatUgx(PLAN_AMOUNT_UGX)} each month</p>
        </div>

        <Card className="p-5 sm:p-6 space-y-3 text-sm">
          <Row label="Status" value={labelFor(sub)} />
          <Row label="Plan" value={`${formatUgx(PLAN_AMOUNT_UGX)} / month`} />
          {sub?.trialEndsAt && <Row label="Trial ends" value={niceDate(sub.trialEndsAt)} />}
          {sub?.currentPeriodEnd && <Row label="Paid until" value={niceDate(sub.currentPeriodEnd)} />}
        </Card>

        {isOwner ? (
          <Card className="overflow-hidden">
            <div className="border-b border-line px-5 py-4">
              <h2 className="text-lg font-semibold">Pay with mobile money</h2>
              <p className="text-sm text-muted">Send {formatUgx(PLAN_AMOUNT_UGX)} to either number</p>
            </div>
            <div className="space-y-4 p-5">
              <div className="rounded-md bg-bg px-4 py-3">
                <p className="text-xs uppercase tracking-wide text-muted">MTN MoMo</p>
                <p className="font-serif text-xl font-semibold tracking-wide">{PAY_MTN}</p>
              </div>
              <div className="rounded-md bg-bg px-4 py-3">
                <p className="text-xs uppercase tracking-wide text-muted">Airtel Money</p>
                <p className="font-serif text-xl font-semibold tracking-wide">{PAY_AIRTEL}</p>
              </div>
              <p className="text-sm text-muted">Use your shop name as the reason if asked.</p>
              {sub?.status === "pending" ? (
                <p className="rounded-md bg-warn-bg px-3 py-3 text-sm text-warn">
                  We have your payment note. Access opens after the transfer is checked.
                </p>
              ) : (
                <form
                  className="space-y-3"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    try {
                      const ws = await claimPayment({ data: { phone, txId, note } });
                      applyWorkspace(ws);
                      setSub(ws.subscription);
                      toast.success("Payment note sent.");
                    } catch (err) {
                      toast.error(err instanceof Error ? err.message : "Could not send.");
                    }
                  }}
                >
                  <Field label="Phone you paid from">
                    <input value={phone} onChange={(e) => setPhone(e.target.value)} className={fieldClass} placeholder="07…" />
                  </Field>
                  <Field label="Transaction ID">
                    <input value={txId} onChange={(e) => setTxId(e.target.value)} className={fieldClass} placeholder="From the SMS" />
                  </Field>
                  <Field label="Note">
                    <input value={note} onChange={(e) => setNote(e.target.value)} className={fieldClass} />
                  </Field>
                  <PrimaryButton type="submit" className="w-full">
                    I have paid {formatUgx(PLAN_AMOUNT_UGX)}
                  </PrimaryButton>
                </form>
              )}
            </div>
          </Card>
        ) : (
          <p className="text-sm text-muted">Ask the shop owner to renew.</p>
        )}
      </div>
    </AppShell>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function labelFor(sub: Subscription | null) {
  if (!sub) return "—";
  if (sub.status === "active" && sub.active) return "Active";
  if (sub.status === "trial" && sub.active) return "Trial";
  if (sub.status === "pending") return "Waiting to confirm";
  if (sub.status === "suspended") return "Suspended";
  return "Ended";
}

function niceDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-UG", { day: "numeric", month: "short", year: "numeric" });
}
