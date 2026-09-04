import { Link, useRouterState } from "@tanstack/react-router";
import { Package, ShoppingBag } from "lucide-react";
import { SignedIn, SignedOut, UserButton } from "@/lib/auth/gates";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { useShop } from "@/lib/store";
import { cn } from "@/lib/cn";
import { SettingsMenu } from "@/components/settings-menu";
import { WorkspaceSync } from "@/components/workspace-sync";

const NAV = [
  { to: "/", label: "Inventory", icon: Package },
  { to: "/sales", label: "Sell", icon: ShoppingBag },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const company = useShop((s) => s.companyName);
  const subActive = useShop((s) => s.subActive);
  const subStatus = useShop((s) => s.subStatus);
  const initial = company.trim().charAt(0).toUpperCase() || "S";
  const { isPending } = useCurrentUserState();

  return (
    <div className="min-h-dvh bg-bg text-ink">
      <WorkspaceSync />
      <header className="sticky top-0 z-30 border-b border-line/80 bg-bg/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-3 px-4 sm:h-16 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary font-serif text-sm font-semibold text-primary-fg">
              {initial}
            </div>
            <div className="min-w-0">
              <p className="truncate font-serif text-base font-semibold leading-tight">{company}</p>
              <p className="text-xs leading-tight text-muted">Shop book</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <nav className="hidden items-center gap-1 md:flex">
              {NAV.map((item) => {
                const active = pathname === item.to;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={cn(
                      "rounded-md px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-good-bg font-medium text-primary"
                        : "text-muted hover:bg-surface hover:text-ink",
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <SettingsMenu />
            {isPending ? (
              <div className="h-8 w-16 animate-pulse rounded-md bg-line/70" />
            ) : (
              <>
                <SignedIn>
                  <div className="hidden sm:block">
                    <UserButton />
                  </div>
                  <Link
                    to="/login"
                    className="inline-flex h-10 items-center rounded-md px-2 text-sm font-medium text-muted sm:hidden"
                  >
                    Account
                  </Link>
                </SignedIn>
                <SignedOut>
                  <Link
                    to="/login"
                    className="inline-flex h-10 items-center rounded-md bg-primary px-3 text-sm font-semibold text-primary-fg"
                  >
                    Sign in
                  </Link>
                </SignedOut>
              </>
            )}
          </div>
        </div>
      </header>

      {!subActive && (
        <div className="border-b border-danger/20 bg-danger-bg">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm text-danger sm:px-6">
            <span>This shop is paused. You can look, but you cannot sell or add stock.</span>
            <Link to="/billing" className="font-medium underline">
              {subStatus === "pending" ? "Payment waiting" : "Pay to reopen"}
            </Link>
          </div>
        </div>
      )}

      <main className="mx-auto w-full max-w-5xl px-4 pb-24 pt-6 sm:px-6 sm:pb-10 sm:pt-8">
        {children}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface md:hidden">
        <div className="grid grid-cols-2">
          {NAV.map((item) => {
            const active = pathname === item.to;
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 text-xs",
                  active ? "text-primary" : "text-muted",
                )}
              >
                <Icon className="size-5" strokeWidth={active ? 2.2 : 1.8} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
