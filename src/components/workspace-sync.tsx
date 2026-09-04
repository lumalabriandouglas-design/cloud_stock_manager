import { useEffect } from "react";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { loadWorkspace } from "@/lib/shop-api";
import { useShop } from "@/lib/store";

export function WorkspaceSync() {
  const { user, isPending } = useCurrentUserState();
  const applyWorkspace = useShop((s) => s.applyWorkspace);

  useEffect(() => {
    if (isPending || !user) return;
    let alive = true;
    loadWorkspace()
      .then((ws) => {
        if (alive) applyWorkspace(ws);
      })
      .catch(() => {
        /* stay on local ledger if the cloud shop is not ready */
      });
    return () => {
      alive = false;
    };
  }, [user, isPending, applyWorkspace]);

  return null;
}
