import { cn } from "@/lib/cn";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={cn("rounded-lg bg-surface shadow-card", className)}>
      {children}
    </section>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      {children}
    </label>
  );
}

export const fieldClass =
  "h-11 w-full rounded-md border border-line bg-bg px-3 text-sm text-ink outline-none transition-shadow focus:border-primary focus:shadow-[0_0_0_3px_rgba(33,92,69,0.15)]";

export function PrimaryButton({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-fg transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function GhostButton({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-md px-3 text-sm font-medium text-muted transition-colors hover:bg-bg hover:text-ink disabled:opacity-40",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function StockPill({ qty, reorder }: { qty: number; reorder: number }) {
  if (qty === 0) {
    return (
      <span className="inline-flex rounded-full bg-danger-bg px-2 py-0.5 text-xs font-medium text-danger">
        Out
      </span>
    );
  }
  if (qty <= reorder) {
    return (
      <span className="inline-flex rounded-full bg-warn-bg px-2 py-0.5 text-xs font-medium text-warn">
        {qty} low
      </span>
    );
  }
  return <span className="tabular-nums text-ink">{qty}</span>;
}
