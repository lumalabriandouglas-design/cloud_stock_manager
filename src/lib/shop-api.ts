import { createServerFn } from "@tanstack/react-start";
import { authMiddleware } from "@/lib/auth/middleware";
import { PLAN_AMOUNT_UGX, TRIAL_DAYS, isSubActive } from "@/lib/billing";
import { SEED } from "@/lib/seed";
import type { Activity, Category, Item, Sale } from "@/lib/types";

function nid(prefix: string) {
  return `${prefix}_${crypto.randomUUID().slice(0, 8)}`;
}

function titleCase(name: string) {
  return name.trim().replace(/\s+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

async function userRow(sql: Awaited<ReturnType<typeof import("@/lib/db").getSql>>, userId: string) {
  const rows = await sql<{ id: string; email: string; name: string }>`
    select id, email, name from "user" where id = ${userId} limit 1
  `;
  return rows[0] ?? { id: userId, email: "", name: "" };
}

export type Membership = {
  id: string;
  userId: string;
  email: string;
  name: string;
  role: "owner" | "staff";
  canManageStock: boolean;
  canEditItems: boolean;
  canViewReports: boolean;
  canManageCategories: boolean;
  canManageTeam: boolean;
};

export type Subscription = {
  id: string;
  status: string;
  trialEndsAt: string | null;
  currentPeriodEnd: string | null;
  lastPaymentAt: string | null;
  paymentPhone: string;
  paymentTxId: string;
  paymentNote: string;
  paymentClaimedAt: string | null;
  active: boolean;
};

export type Workspace = {
  companyId: string;
  companyName: string;
  isPlatformAdmin: boolean;
  membership: Membership;
  subscription: Subscription;
  members: Membership[];
  invites: { id: string; email: string; role: string }[];
  categories: Category[];
  items: Item[];
  sales: Sale[];
  activity: Activity[];
};

function mapMember(row: {
  id: string;
  user_id: string;
  email: string;
  name: string;
  role: string;
  can_manage_stock: boolean;
  can_edit_items: boolean;
  can_view_reports: boolean;
  can_manage_categories: boolean;
  can_manage_team: boolean;
}): Membership {
  return {
    id: row.id,
    userId: row.user_id,
    email: row.email,
    name: row.name,
    role: row.role === "owner" ? "owner" : "staff",
    canManageStock: row.can_manage_stock,
    canEditItems: row.can_edit_items,
    canViewReports: row.can_view_reports,
    canManageCategories: row.can_manage_categories,
    canManageTeam: row.can_manage_team,
  };
}

async function loadForCompany(
  sql: Awaited<ReturnType<typeof import("@/lib/db").getSql>>,
  companyId: string,
  userId: string,
): Promise<Workspace> {
  const companies = await sql<{ id: string; name: string }>`
    select id, name from companies where id = ${companyId} limit 1
  `;
  const company = companies[0];
  const memRows = await sql<{
    id: string;
    user_id: string;
    email: string;
    name: string;
    role: string;
    can_manage_stock: boolean;
    can_edit_items: boolean;
    can_view_reports: boolean;
    can_manage_categories: boolean;
    can_manage_team: boolean;
  }>`
    select * from memberships where company_id = ${companyId}
  `;
  const members = memRows.map(mapMember);
  const mine = members.find((m) => m.userId === userId);
  if (!mine) throw new Error("You are not on this shop.");
  const subRows = await sql<{
    id: string;
    status: string;
    trial_ends_at: string | null;
    current_period_end: string | null;
    last_payment_at: string | null;
    payment_phone: string;
    payment_tx_id: string;
    payment_note: string;
    payment_claimed_at: string | null;
  }>`
    select * from subscriptions where company_id = ${companyId} limit 1
  `;
  const raw = subRows[0];
  const subscription: Subscription = {
    id: raw?.id ?? "",
    status: raw?.status ?? "suspended",
    trialEndsAt: raw?.trial_ends_at ?? null,
    currentPeriodEnd: raw?.current_period_end ?? null,
    lastPaymentAt: raw?.last_payment_at ?? null,
    paymentPhone: raw?.payment_phone ?? "",
    paymentTxId: raw?.payment_tx_id ?? "",
    paymentNote: raw?.payment_note ?? "",
    paymentClaimedAt: raw?.payment_claimed_at ?? null,
    active: raw
      ? isSubActive({
          status: raw.status,
          trialEndsAt: raw.trial_ends_at,
          currentPeriodEnd: raw.current_period_end,
        })
      : false,
  };
  const cats = await sql<{ id: string; name: string }>`
    select id, name from categories where company_id = ${companyId} order by name
  `;
  const itemRows = await sql<{
    id: string;
    name: string;
    category_id: string | null;
    buy_price: number;
    sell_price: number;
    quantity: number;
    reorder_level: number;
  }>`
    select * from items where company_id = ${companyId} order by name
  `;
  const saleRows = await sql<{
    id: string;
    item_id: string | null;
    item_name: string;
    quantity: number;
    sell_price: number;
    cost_price: number;
    created_at: string;
  }>`
    select * from sales where company_id = ${companyId} order by created_at desc limit 200
  `;
  const actRows = await sql<{
    id: string;
    kind: string;
    message: string;
    created_at: string;
  }>`
    select * from activities where company_id = ${companyId} order by created_at desc limit 40
  `;
  const inviteRows = await sql<{ id: string; email: string; role: string }>`
    select id, email, role from invites where company_id = ${companyId} order by created_at desc
  `;
  const admins = await sql<{ user_id: string }>`
    select user_id from platform_admins where user_id = ${userId} limit 1
  `;
  return {
    companyId,
    companyName: company?.name ?? "Shop",
    isPlatformAdmin: admins.length > 0,
    membership: mine,
    subscription,
    members,
    invites: inviteRows,
    categories: cats,
    items: itemRows.map((it) => ({
      id: it.id,
      name: it.name,
      categoryId: it.category_id,
      buyPrice: Number(it.buy_price),
      sellPrice: Number(it.sell_price),
      quantity: Number(it.quantity),
      reorderLevel: Number(it.reorder_level),
    })),
    sales: saleRows.map((s) => ({
      id: s.id,
      itemId: s.item_id ?? "",
      itemName: s.item_name,
      quantity: Number(s.quantity),
      sellPrice: Number(s.sell_price),
      costPrice: Number(s.cost_price),
      createdAt: s.created_at,
    })),
    activity: actRows.map((a) => ({
      id: a.id,
      kind: a.kind === "sale" || a.kind === "stock" ? a.kind : "edit",
      message: a.message,
      createdAt: a.created_at,
    })),
  };
}

export const loadWorkspace = createServerFn({ method: "GET" })
  .middleware([authMiddleware])
  .handler(async ({ context }) => {
    const { importLegacyShop } = await import("@/lib/legacy");
    await importLegacyShop();
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const me = await userRow(sql, context.userId);

    const adminCount = await sql<{ n: number }>`select count(*)::int as n from platform_admins`;
    if (Number(adminCount[0]?.n ?? 0) === 0) {
      await sql`
        insert into platform_admins (user_id, email)
        values (${context.userId}, ${me.email})
        on conflict (user_id) do nothing
      `;
    }

    const pending = await sql<{
      id: string;
      company_id: string;
      role: string;
      can_manage_stock: boolean;
      can_edit_items: boolean;
      can_view_reports: boolean;
      can_manage_categories: boolean;
      can_manage_team: boolean;
    }>`
      select * from invites where lower(email) = ${me.email.toLowerCase()}
    `;
    for (const inv of pending) {
      const exists = await sql<{ id: string }>`
        select id from memberships
        where company_id = ${inv.company_id} and user_id = ${context.userId}
        limit 1
      `;
      if (exists.length === 0) {
        await sql`
          insert into memberships (
            id, company_id, user_id, email, name, role,
            can_manage_stock, can_edit_items, can_view_reports,
            can_manage_categories, can_manage_team
          ) values (
            ${nid("mb")}, ${inv.company_id}, ${context.userId}, ${me.email}, ${me.name}, ${inv.role},
            ${inv.can_manage_stock}, ${inv.can_edit_items}, ${inv.can_view_reports},
            ${inv.can_manage_categories}, ${inv.can_manage_team}
          )
        `;
      }
      await sql`delete from invites where id = ${inv.id}`;
    }

    let membership = await sql<{ company_id: string }>`
      select company_id from memberships where user_id = ${context.userId} order by created_at asc limit 1
    `;
    if (membership.length === 0) {
      const companyId = nid("co");
      const subId = nid("sub");
      const trialEnd = new Date(Date.now() + TRIAL_DAYS * 86400000).toISOString();
      await sql`
        insert into companies (id, name, owner_user_id)
        values (${companyId}, ${me.name ? `${me.name}'s shop` : "My shop"}, ${context.userId})
      `;
      await sql`
        insert into subscriptions (id, company_id, status, trial_ends_at)
        values (${subId}, ${companyId}, 'trial', ${trialEnd})
      `;
      await sql`
        insert into memberships (
          id, company_id, user_id, email, name, role,
          can_manage_stock, can_edit_items, can_view_reports,
          can_manage_categories, can_manage_team
        ) values (
          ${nid("mb")}, ${companyId}, ${context.userId}, ${me.email}, ${me.name}, 'owner',
          true, true, true, true, true
        )
      `;
      for (const cat of SEED.categories) {
        await sql`insert into categories (id, company_id, name) values (${cat.id}, ${companyId}, ${cat.name})`;
      }
      for (const item of SEED.items) {
        await sql`
          insert into items (id, company_id, name, category_id, buy_price, sell_price, quantity, reorder_level)
          values (${item.id}, ${companyId}, ${item.name}, ${item.categoryId}, ${item.buyPrice}, ${item.sellPrice}, ${item.quantity}, ${item.reorderLevel})
        `;
      }
      membership = [{ company_id: companyId }];
    }
    return loadForCompany(sql, membership[0].company_id, context.userId);
  });

export const saveCompanyName = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((name: string) => name.trim())
  .handler(async ({ context, data: name }) => {
    const ws = await loadWorkspace();
    if (ws.membership.role !== "owner") throw new Error("Only the owner can rename the shop.");
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    await sql`update companies set name = ${name || ws.companyName} where id = ${ws.companyId}`;
    return loadWorkspace();
  });

export const persistItem = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((draft: {
    id?: string;
    name: string;
    categoryId: string | null;
    buyPrice: number;
    sellPrice: number;
    quantity?: number;
    reorderLevel: number;
  }) => draft)
  .handler(async ({ context, data: draft }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canEditItems && ws.membership.role !== "owner") {
      throw new Error("You cannot edit products.");
    }
    if (!ws.subscription.active) throw new Error("Subscription is not active.");
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const name = titleCase(draft.name);
    if (draft.id) {
      if (draft.quantity === undefined) {
        await sql`
          update items set
            name = ${name},
            category_id = ${draft.categoryId},
            buy_price = ${Math.round(draft.buyPrice)},
            sell_price = ${Math.round(draft.sellPrice)},
            reorder_level = ${Math.round(draft.reorderLevel)}
          where id = ${draft.id} and company_id = ${ws.companyId}
        `;
      } else {
        await sql`
          update items set
            name = ${name},
            category_id = ${draft.categoryId},
            buy_price = ${Math.round(draft.buyPrice)},
            sell_price = ${Math.round(draft.sellPrice)},
            quantity = ${Math.round(draft.quantity)},
            reorder_level = ${Math.round(draft.reorderLevel)}
          where id = ${draft.id} and company_id = ${ws.companyId}
        `;
      }
      await sql`
        insert into activities (id, company_id, kind, message)
        values (${nid("ac")}, ${ws.companyId}, 'edit', ${`Updated ${name}`})
      `;
    } else {
      await sql`
        insert into items (id, company_id, name, category_id, buy_price, sell_price, quantity, reorder_level)
        values (
          ${nid("it")}, ${ws.companyId}, ${name}, ${draft.categoryId},
          ${Math.round(draft.buyPrice)}, ${Math.round(draft.sellPrice)},
          ${Math.round(draft.quantity ?? 0)}, ${Math.round(draft.reorderLevel)}
        )
      `;
    }
    return loadWorkspace();
  });

export const persistReceive = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((input: {
    itemId?: string;
    name: string;
    quantity: number;
    buyPrice?: number;
    sellPrice?: number;
    categoryId?: string | null;
  }) => input)
  .handler(async ({ data: input }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canManageStock && ws.membership.role !== "owner") {
      throw new Error("You cannot add stock.");
    }
    if (!ws.subscription.active) throw new Error("Subscription is not active.");
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const qty = Math.floor(input.quantity);
    if (qty < 1) throw new Error("Quantity must be at least 1.");
    const name = titleCase(input.name);
    let item = input.itemId
      ? ws.items.find((it) => it.id === input.itemId)
      : ws.items.find((it) => it.name.toLowerCase() === name.toLowerCase());
    if (!item) {
      const id = nid("it");
      await sql`
        insert into items (id, company_id, name, category_id, buy_price, sell_price, quantity, reorder_level)
        values (${id}, ${ws.companyId}, ${name}, ${input.categoryId ?? null}, ${Math.round(input.buyPrice ?? 0)}, ${Math.round(input.sellPrice ?? 0)}, ${qty}, 5)
      `;
      item = { id, name, categoryId: input.categoryId ?? null, buyPrice: input.buyPrice ?? 0, sellPrice: input.sellPrice ?? 0, quantity: qty, reorderLevel: 5 };
    } else {
      await sql`
        update items set
          quantity = quantity + ${qty},
          buy_price = ${Math.round(input.buyPrice ?? item.buyPrice)},
          sell_price = ${Math.round(input.sellPrice ?? item.sellPrice)}
        where id = ${item.id} and company_id = ${ws.companyId}
      `;
    }
    await sql`
      insert into stock_moves (id, company_id, item_id, item_name, quantity)
      values (${nid("st")}, ${ws.companyId}, ${item.id}, ${item.name}, ${qty})
    `;
    await sql`
      insert into activities (id, company_id, kind, message)
      values (${nid("ac")}, ${ws.companyId}, 'stock', ${`Added ${qty} × ${item.name}`})
    `;
    return loadWorkspace();
  });

export const persistSale = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((input: { itemId: string; quantity: number; sellPrice?: number }) => input)
  .handler(async ({ data: input }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canManageStock && ws.membership.role !== "owner") {
      throw new Error("You cannot record sales.");
    }
    if (!ws.subscription.active) throw new Error("Subscription is not active.");
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const item = ws.items.find((it) => it.id === input.itemId);
    if (!item) throw new Error("Product not found.");
    const qty = Math.floor(input.quantity);
    if (item.quantity < qty) throw new Error(`Only ${item.quantity} in stock.`);
    const price = Math.round(input.sellPrice ?? item.sellPrice);
    await sql`update items set quantity = quantity - ${qty} where id = ${item.id} and company_id = ${ws.companyId}`;
    await sql`
      insert into sales (id, company_id, item_id, item_name, quantity, sell_price, cost_price)
      values (${nid("sa")}, ${ws.companyId}, ${item.id}, ${item.name}, ${qty}, ${price}, ${Math.round(item.buyPrice)})
    `;
    await sql`
      insert into activities (id, company_id, kind, message)
      values (${nid("ac")}, ${ws.companyId}, 'sale', ${`Sold ${qty} × ${item.name}`})
    `;
    return loadWorkspace();
  });

export const persistDeleteItem = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((id: string) => id)
  .handler(async ({ data: id }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canEditItems && ws.membership.role !== "owner") {
      throw new Error("You cannot remove products.");
    }
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    await sql`delete from items where id = ${id} and company_id = ${ws.companyId}`;
    return loadWorkspace();
  });

export const persistCategory = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((name: string) => titleCase(name))
  .handler(async ({ data: name }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canManageCategories && ws.membership.role !== "owner") {
      throw new Error("You cannot manage groups.");
    }
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const id = nid("cat");
    await sql`insert into categories (id, company_id, name) values (${id}, ${ws.companyId}, ${name})`;
    return { id, workspace: await loadWorkspace() };
  });

export const inviteStaff = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((input: {
    email: string;
    role: "owner" | "staff";
    canManageStock: boolean;
    canEditItems: boolean;
    canViewReports: boolean;
    canManageCategories: boolean;
    canManageTeam: boolean;
  }) => ({ ...input, email: input.email.trim().toLowerCase() }))
  .handler(async ({ data }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canManageTeam && ws.membership.role !== "owner") {
      throw new Error("You cannot invite staff.");
    }
    if (data.role === "owner" && ws.membership.role !== "owner") {
      throw new Error("Only the shop owner can add another owner.");
    }
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const existingUser = await sql<{ id: string; name: string; email: string }>`
      select id, name, email from "user" where lower(email) = ${data.email} limit 1
    `;
    if (existingUser[0]) {
      const already = await sql<{ id: string }>`
        select id from memberships where company_id = ${ws.companyId} and user_id = ${existingUser[0].id} limit 1
      `;
      if (already.length === 0) {
        await sql`
          insert into memberships (
            id, company_id, user_id, email, name, role,
            can_manage_stock, can_edit_items, can_view_reports,
            can_manage_categories, can_manage_team
          ) values (
            ${nid("mb")}, ${ws.companyId}, ${existingUser[0].id}, ${data.email}, ${existingUser[0].name}, ${data.role},
            ${data.canManageStock}, ${data.canEditItems}, ${data.canViewReports},
            ${data.canManageCategories}, ${data.canManageTeam}
          )
        `;
      }
    } else {
      await sql`
        insert into invites (
          id, company_id, email, role,
          can_manage_stock, can_edit_items, can_view_reports,
          can_manage_categories, can_manage_team
        ) values (
          ${nid("inv")}, ${ws.companyId}, ${data.email}, ${data.role},
          ${data.canManageStock}, ${data.canEditItems}, ${data.canViewReports},
          ${data.canManageCategories}, ${data.canManageTeam}
        )
      `;
    }
    return loadWorkspace();
  });

export const updateMemberPerms = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((input: {
    membershipId: string;
    canManageStock: boolean;
    canEditItems: boolean;
    canViewReports: boolean;
    canManageCategories: boolean;
    canManageTeam: boolean;
  }) => input)
  .handler(async ({ data }) => {
    const ws = await loadWorkspace();
    if (!ws.membership.canManageTeam && ws.membership.role !== "owner") {
      throw new Error("You cannot change permissions.");
    }
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    await sql`
      update memberships set
        can_manage_stock = ${data.canManageStock},
        can_edit_items = ${data.canEditItems},
        can_view_reports = ${data.canViewReports},
        can_manage_categories = ${data.canManageCategories},
        can_manage_team = ${data.canManageTeam}
      where id = ${data.membershipId} and company_id = ${ws.companyId} and role <> 'owner'
    `;
    return loadWorkspace();
  });

export const removeMember = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((membershipId: string) => membershipId)
  .handler(async ({ data: membershipId }) => {
    const ws = await loadWorkspace();
    if (ws.membership.role !== "owner") throw new Error("Only the owner can remove staff.");
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    await sql`
      delete from memberships
      where id = ${membershipId} and company_id = ${ws.companyId} and role <> 'owner'
    `;
    return loadWorkspace();
  });

export const claimPayment = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((input: { phone: string; txId: string; note: string }) => input)
  .handler(async ({ data }) => {
    const ws = await loadWorkspace();
    if (ws.membership.role !== "owner") throw new Error("Only the owner can send payment proof.");
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    await sql`
      update subscriptions set
        status = 'pending',
        payment_phone = ${data.phone.slice(0, 20)},
        payment_tx_id = ${data.txId.slice(0, 100)},
        payment_note = ${data.note.slice(0, 255)},
        payment_claimed_at = now(),
        updated_at = now()
      where company_id = ${ws.companyId}
    `;
    return loadWorkspace();
  });

export type PlatformCompany = {
  id: string;
  name: string;
  ownerEmail: string;
  status: string;
  active: boolean;
  trialEndsAt: string | null;
  currentPeriodEnd: string | null;
  paymentTxId: string;
  paymentPhone: string;
  claimedAt: string | null;
};

export const listPlatformCompanies = createServerFn({ method: "GET" })
  .middleware([authMiddleware])
  .handler(async ({ context }) => {
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const admin = await sql<{ user_id: string }>`
      select user_id from platform_admins where user_id = ${context.userId} limit 1
    `;
    if (admin.length === 0) throw new Error("Platform access only.");
    const rows = await sql<{
      id: string;
      name: string;
      email: string;
      status: string;
      trial_ends_at: string | null;
      current_period_end: string | null;
      payment_tx_id: string;
      payment_phone: string;
      payment_claimed_at: string | null;
    }>`
      select c.id, c.name, coalesce(u.email, '') as email,
        s.status, s.trial_ends_at, s.current_period_end,
        s.payment_tx_id, s.payment_phone, s.payment_claimed_at
      from companies c
      left join subscriptions s on s.company_id = c.id
      left join "user" u on u.id = c.owner_user_id
      order by c.created_at desc
    `;
    return rows.map((r) => ({
      id: r.id,
      name: r.name,
      ownerEmail: r.email,
      status: r.status,
      active: isSubActive({
        status: r.status,
        trialEndsAt: r.trial_ends_at,
        currentPeriodEnd: r.current_period_end,
      }),
      trialEndsAt: r.trial_ends_at,
      currentPeriodEnd: r.current_period_end,
      paymentTxId: r.payment_tx_id,
      paymentPhone: r.payment_phone,
      claimedAt: r.payment_claimed_at,
    })) satisfies PlatformCompany[];
  });

export const platformAct = createServerFn({ method: "POST" })
  .middleware([authMiddleware])
  .validator((input: { companyId: string; action: "activate" | "suspend" | "extend" | "delete" }) => input)
  .handler(async ({ context, data }) => {
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const admin = await sql<{ user_id: string }>`
      select user_id from platform_admins where user_id = ${context.userId} limit 1
    `;
    if (admin.length === 0) throw new Error("Platform access only.");
    if (data.action === "delete") {
      await sql`delete from companies where id = ${data.companyId}`;
    } else if (data.action === "suspend") {
      await sql`update subscriptions set status = 'suspended', updated_at = now() where company_id = ${data.companyId}`;
    } else if (data.action === "activate" || data.action === "extend") {
      const end = new Date(Date.now() + 30 * 86400000).toISOString();
      await sql`
        update subscriptions set
          status = 'active',
          last_payment_at = now(),
          current_period_end = ${end},
          updated_at = now()
        where company_id = ${data.companyId}
      `;
    }
    return listPlatformCompanies();
  });

export { PLAN_AMOUNT_UGX };
