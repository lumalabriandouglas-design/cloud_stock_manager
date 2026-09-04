import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card, Field, GhostButton, PrimaryButton, fieldClass } from "@/components/ui-bits";
import {
  inviteStaff,
  loadWorkspace,
  removeMember,
  updateMemberPerms,
  type Membership,
} from "@/lib/shop-api";
import { useShop } from "@/lib/store";

export const Route = createFileRoute("/team")({ component: TeamPage });

function TeamPage() {
  const applyWorkspace = useShop((s) => s.applyWorkspace);
  const canManageTeam = useShop((s) => s.canManageTeam);
  const isOwner = useShop((s) => s.isOwner);
  const [members, setMembers] = useState<Membership[]>([]);
  const [invites, setInvites] = useState<{ id: string; email: string; role: string }[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"staff" | "owner">("staff");
  const [perms, setPerms] = useState({
    canManageStock: true,
    canEditItems: true,
    canViewReports: true,
    canManageCategories: false,
    canManageTeam: false,
  });

  useEffect(() => {
    loadWorkspace()
      .then((ws) => {
        applyWorkspace(ws);
        setMembers(ws.members);
        setInvites(ws.invites);
      })
      .catch((err) => toast.error(err instanceof Error ? err.message : "Sign in first."));
  }, [applyWorkspace]);

  if (!canManageTeam) {
    return (
      <AppShell>
        <p className="text-sm text-muted">Only a shop owner or team manager can open this page.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Staff</h1>
          <p className="mt-1 text-sm text-muted">Invite someone. Tick only what they may do.</p>
        </div>

        <Card className="p-5 sm:p-6">
          <h2 className="mb-4 text-lg font-semibold">Invite</h2>
          <form
            className="space-y-4"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const ws = await inviteStaff({ data: { email, role, ...perms } });
                applyWorkspace(ws);
                setMembers(ws.members);
                setInvites(ws.invites);
                setEmail("");
                toast.success("Invite saved. They join when they sign in with that email.");
              } catch (err) {
                toast.error(err instanceof Error ? err.message : "Could not invite.");
              }
            }}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Their email">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={fieldClass}
                />
              </Field>
              <Field label="Role">
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as "staff" | "owner")}
                  className={fieldClass}
                  disabled={!isOwner}
                >
                  <option value="staff">Staff</option>
                  {isOwner && <option value="owner">Owner</option>}
                </select>
              </Field>
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
              {(
                [
                  ["canManageStock", "Stock & sell"],
                  ["canEditItems", "Edit products"],
                  ["canViewReports", "Reports"],
                  ["canManageCategories", "Groups"],
                  ["canManageTeam", "Manage staff"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={perms[key]}
                    onChange={(e) => setPerms((p) => ({ ...p, [key]: e.target.checked }))}
                  />
                  {label}
                </label>
              ))}
            </div>
            <PrimaryButton type="submit">Send invite</PrimaryButton>
          </form>
        </Card>

        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <h2 className="text-lg font-semibold">On this shop</h2>
          </div>
          <ul className="divide-y divide-line">
            {members.map((m) => (
              <li key={m.id} className="space-y-2 px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{m.name || m.email || "Member"}</p>
                    <p className="text-xs text-muted">
                      {m.email} · {m.role === "owner" ? "Owner · full access" : "Staff"}
                    </p>
                  </div>
                  {m.role !== "owner" && (
                    <GhostButton
                      className="h-9 text-danger"
                      onClick={async () => {
                        const ws = await removeMember({ data: m.id });
                        applyWorkspace(ws);
                        setMembers(ws.members);
                      }}
                    >
                      Remove
                    </GhostButton>
                  )}
                </div>
                {m.role !== "owner" && (
                  <PermRow
                    member={m}
                    onSave={async (next) => {
                      const ws = await updateMemberPerms({
                        data: { membershipId: m.id, ...next },
                      });
                      applyWorkspace(ws);
                      setMembers(ws.members);
                      toast.success("Saved");
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        </Card>

        {invites.length > 0 && (
          <p className="text-sm text-muted">
            Waiting to join: {invites.map((i) => i.email).join(", ")}
          </p>
        )}
      </div>
    </AppShell>
  );
}

function PermRow({
  member,
  onSave,
}: {
  member: Membership;
  onSave: (p: {
    canManageStock: boolean;
    canEditItems: boolean;
    canViewReports: boolean;
    canManageCategories: boolean;
    canManageTeam: boolean;
  }) => void;
}) {
  const [p, setP] = useState({
    canManageStock: member.canManageStock,
    canEditItems: member.canEditItems,
    canViewReports: member.canViewReports,
    canManageCategories: member.canManageCategories,
    canManageTeam: member.canManageTeam,
  });
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs">
      {(
        [
          ["canManageStock", "Stock"],
          ["canEditItems", "Edit"],
          ["canViewReports", "Reports"],
          ["canManageCategories", "Groups"],
          ["canManageTeam", "Team"],
        ] as const
      ).map(([key, label]) => (
        <label key={key} className="inline-flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={p[key]}
            onChange={(e) => setP((cur) => ({ ...cur, [key]: e.target.checked }))}
          />
          {label}
        </label>
      ))}
      <button type="button" className="font-medium text-primary" onClick={() => onSave(p)}>
        Save
      </button>
    </div>
  );
}
