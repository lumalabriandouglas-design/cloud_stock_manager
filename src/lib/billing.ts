export const PLAN_AMOUNT_UGX = 15000;
export const TRIAL_DAYS = 7;
export const PAY_MTN = "0781 085 183";
export const PAY_AIRTEL = "0755 548 624";

export type SubStatus = "trial" | "active" | "pending" | "past_due" | "suspended";

export function isSubActive(sub: {
  status: string;
  trialEndsAt: string | null;
  currentPeriodEnd: string | null;
}): boolean {
  const now = Date.now();
  if (sub.status === "active") {
    if (sub.currentPeriodEnd && new Date(sub.currentPeriodEnd).getTime() < now) return false;
    return true;
  }
  if (sub.status === "trial") {
    return Boolean(sub.trialEndsAt && new Date(sub.trialEndsAt).getTime() >= now);
  }
  return false;
}
