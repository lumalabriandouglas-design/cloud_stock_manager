import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { InventoryScreen } from "@/components/inventory-screen";

type Search = { low?: string };

export const Route = createFileRoute("/")({
  validateSearch: (s: Record<string, unknown>): Search => ({
    low: typeof s.low === "string" ? s.low : undefined,
  }),
  component: Home,
});

function Home() {
  const { low } = Route.useSearch();
  const navigate = useNavigate({ from: "/" });
  return (
    <InventoryScreen
      low={low}
      onToggleLow={() => navigate({ search: low === "1" ? {} : { low: "1" } })}
    />
  );
}
