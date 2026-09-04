import { createFileRoute, Navigate } from "@tanstack/react-router";

type Search = { low?: string };

export const Route = createFileRoute("/stock")({
  validateSearch: (s: Record<string, unknown>): Search => ({
    low: typeof s.low === "string" ? s.low : undefined,
  }),
  component: StockRedirect,
});

function StockRedirect() {
  const { low } = Route.useSearch();
  return <Navigate to="/" search={low ? { low } : {}} />;
}
