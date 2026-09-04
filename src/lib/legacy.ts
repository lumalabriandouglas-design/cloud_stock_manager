import { createServerFn } from "@tanstack/react-start";
import { pbkdf2, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";
import { hashPassword } from "better-auth/crypto";

const pbkdf2Async = promisify(pbkdf2);

function nid(prefix: string, raw: string | number) {
  return `${prefix}-${raw}`;
}

function emailFor(username: string, email: string) {
  const trimmed = email.trim().toLowerCase();
  if (trimmed.includes("@")) return trimmed;
  return `${username.trim().toLowerCase()}@legacy.local`;
}

export async function verifyDjangoPassword(password: string, encoded: string) {
  const parts = encoded.split("$");
  if (parts.length !== 4) return false;
  const algo = parts[0];
  if (algo !== "pbkdf2_sha256" && algo !== "pbkdf2_sha1") return false;
  const iterations = Number(parts[1]);
  const salt = parts[2];
  const expected = Buffer.from(parts[3], "base64");
  if (!iterations || expected.length === 0) return false;
  const digest = await pbkdf2Async(
    password,
    salt,
    iterations,
    expected.length,
    algo === "pbkdf2_sha1" ? "sha1" : "sha256",
  );
  if (digest.length !== expected.length) return false;
  return timingSafeEqual(digest, expected);
}

async function tableExists(
  sql: Awaited<ReturnType<typeof import("@/lib/db").getSql>>,
  name: string,
) {
  const rows = await sql<{ exists: boolean }>`
    select to_regclass(${"public." + name}) is not null as exists
  `;
  return Boolean(rows[0]?.exists);
}

export async function importLegacyShop() {
  const { getSql } = await import("@/lib/db");
  const sql = await getSql();
  const done = await sql<{ id: string }>`select id from legacy_import_state where id = 'railway' limit 1`;
  if (done.length > 0) return { skipped: true as const };

  const hasCompany = await tableExists(sql, "inventory_company");
  const hasUser = await tableExists(sql, "auth_user");
  if (!hasCompany || !hasUser) {
    return { skipped: true as const, reason: "no-django" };
  }

  const users = await sql.query<{
    id: number;
    username: string;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    is_superuser: boolean;
    is_active: boolean;
  }>(
    `select id, username, email, password, first_name, last_name, is_superuser, is_active from auth_user`,
  );

  for (const u of users) {
    if (!u.is_active) continue;
    const email = emailFor(u.username, u.email);
    await sql`
      insert into legacy_credentials (username, email, django_password, is_superuser, auth_user_id)
      values (${u.username.toLowerCase()}, ${email}, ${u.password}, ${Boolean(u.is_superuser)}, ${nid("dj-user", u.id)})
      on conflict (username) do update set
        email = excluded.email,
        django_password = excluded.django_password,
        is_superuser = excluded.is_superuser
    `;
    if (u.is_superuser) {
      await sql`
        insert into platform_admins (user_id, email)
        values (${nid("dj-user", u.id)}, ${email})
        on conflict (user_id) do nothing
      `;
    }
  }

  const companies = await sql.query<{ id: number; name: string }>(
    `select id, name from inventory_company`,
  );
  for (const c of companies) {
    const owner = await sql.query<{ user_id: number }>(
      `select user_id from inventory_userprofile where company_id = $1 and role = 'owner' order by id asc limit 1`,
      [c.id],
    );
    const ownerId = owner[0] ? nid("dj-user", owner[0].user_id) : nid("dj-user", "unknown");
    await sql`
      insert into companies (id, name, owner_user_id)
      values (${nid("dj-co", c.id)}, ${c.name}, ${ownerId})
      on conflict (id) do update set name = excluded.name
    `;
  }

  if (await tableExists(sql, "inventory_subscription")) {
    const subs = await sql.query<{
      id: number;
      company_id: number;
      status: string;
      trial_ends_at: string | null;
      current_period_end: string | null;
      last_payment_at: string | null;
      payment_phone: string;
      payment_tx_id: string;
      payment_note: string;
      payment_claimed_at: string | null;
    }>(`select * from inventory_subscription`);
    for (const s of subs) {
      await sql`
        insert into subscriptions (
          id, company_id, status, trial_ends_at, current_period_end, last_payment_at,
          payment_phone, payment_tx_id, payment_note, payment_claimed_at
        ) values (
          ${nid("dj-sub", s.id)}, ${nid("dj-co", s.company_id)}, ${s.status},
          ${s.trial_ends_at}, ${s.current_period_end}, ${s.last_payment_at},
          ${s.payment_phone ?? ""}, ${s.payment_tx_id ?? ""}, ${s.payment_note ?? ""},
          ${s.payment_claimed_at}
        )
        on conflict (company_id) do update set
          status = excluded.status,
          trial_ends_at = excluded.trial_ends_at,
          current_period_end = excluded.current_period_end,
          last_payment_at = excluded.last_payment_at,
          payment_phone = excluded.payment_phone,
          payment_tx_id = excluded.payment_tx_id,
          payment_note = excluded.payment_note,
          payment_claimed_at = excluded.payment_claimed_at
      `;
    }
  }

  if (await tableExists(sql, "inventory_userprofile")) {
    const profiles = await sql.query<{
      id: number;
      user_id: number;
      company_id: number;
      role: string;
      can_manage_stock: boolean;
      can_edit_items: boolean;
      can_view_reports: boolean;
      can_manage_categories: boolean;
      can_manage_team: boolean;
    }>(`select * from inventory_userprofile`);
    for (const p of profiles) {
      const cred = users.find((u) => Number(u.id) === Number(p.user_id));
      const email = cred ? emailFor(cred.username, cred.email) : "";
      const name = cred ? [cred.first_name, cred.last_name].filter(Boolean).join(" ") || cred.username : "";
      await sql`
        insert into memberships (
          id, company_id, user_id, email, name, role,
          can_manage_stock, can_edit_items, can_view_reports,
          can_manage_categories, can_manage_team
        ) values (
          ${nid("dj-mb", p.id)}, ${nid("dj-co", p.company_id)}, ${nid("dj-user", p.user_id)},
          ${email}, ${name}, ${p.role === "owner" ? "owner" : "staff"},
          ${Boolean(p.can_manage_stock)}, ${Boolean(p.can_edit_items)}, ${Boolean(p.can_view_reports)},
          ${Boolean(p.can_manage_categories)}, ${Boolean(p.can_manage_team)}
        )
        on conflict (company_id, user_id) do update set
          role = excluded.role,
          email = excluded.email,
          name = excluded.name,
          can_manage_stock = excluded.can_manage_stock,
          can_edit_items = excluded.can_edit_items,
          can_view_reports = excluded.can_view_reports,
          can_manage_categories = excluded.can_manage_categories,
          can_manage_team = excluded.can_manage_team
      `;
    }
  }

  let itemCount = 0;
  if (await tableExists(sql, "inventory_category")) {
    const cats = await sql.query<{ id: number; company_id: number; name: string }>(
      `select id, company_id, name from inventory_category`,
    );
    for (const c of cats) {
      await sql`
        insert into categories (id, company_id, name)
        values (${nid("dj-cat", c.id)}, ${nid("dj-co", c.company_id)}, ${c.name})
        on conflict (id) do nothing
      `;
    }
  }

  if (await tableExists(sql, "inventory_item")) {
    const items = await sql.query<{
      id: number;
      company_id: number;
      name: string;
      category_id: number | null;
      buy_price: string | number;
      sell_price: string | number;
      quantity_in_stock: number;
      reorder_level: number;
    }>(`select * from inventory_item`);
    itemCount = items.length;
    for (const it of items) {
      await sql`
        insert into items (id, company_id, name, category_id, buy_price, sell_price, quantity, reorder_level)
        values (
          ${nid("dj-it", it.id)}, ${nid("dj-co", it.company_id)}, ${it.name},
          ${it.category_id ? nid("dj-cat", it.category_id) : null},
          ${Math.round(Number(it.buy_price) || 0)},
          ${Math.round(Number(it.sell_price) || 0)},
          ${Number(it.quantity_in_stock) || 0},
          ${Number(it.reorder_level) || 5}
        )
        on conflict (id) do update set
          name = excluded.name,
          quantity = excluded.quantity,
          buy_price = excluded.buy_price,
          sell_price = excluded.sell_price,
          reorder_level = excluded.reorder_level
      `;
    }
  }

  if (await tableExists(sql, "inventory_sale")) {
    const sales = await sql.query<{
      id: number;
      company_id: number;
      item_id: number;
      quantity_sold: number;
      sell_price: string | number;
      sales_date: string;
    }>(`select * from inventory_sale`);
    const itemCost = new Map<string, number>();
    const itemRows = await sql<{ id: string; buy_price: number; name: string }>`
      select id, buy_price, name from items
    `;
    for (const row of itemRows) itemCost.set(row.id, Number(row.buy_price));
    const itemName = new Map(itemRows.map((r) => [r.id, r.name]));
    for (const s of sales) {
      const itemId = nid("dj-it", s.item_id);
      await sql`
        insert into sales (id, company_id, item_id, item_name, quantity, sell_price, cost_price, created_at)
        values (
          ${nid("dj-sa", s.id)}, ${nid("dj-co", s.company_id)}, ${itemId},
          ${itemName.get(itemId) ?? "Item"},
          ${Number(s.quantity_sold) || 0},
          ${Math.round(Number(s.sell_price) || 0)},
          ${Math.round(itemCost.get(itemId) ?? 0)},
          ${s.sales_date}
        )
        on conflict (id) do nothing
      `;
    }
  }

  if (await tableExists(sql, "inventory_activitylog")) {
    const acts = await sql.query<{
      id: number;
      company_id: number;
      action: string;
      message: string;
      created_at: string;
    }>(`select id, company_id, action, message, created_at from inventory_activitylog`);
    for (const a of acts) {
      const kind = a.action === "sale" ? "sale" : a.action === "stock_in" ? "stock" : "edit";
      await sql`
        insert into activities (id, company_id, kind, message, created_at)
        values (${nid("dj-ac", a.id)}, ${nid("dj-co", a.company_id)}, ${kind}, ${a.message}, ${a.created_at})
        on conflict (id) do nothing
      `;
    }
  }

  await sql`
    insert into legacy_import_state (id, companies, users, items)
    values ('railway', ${companies.length}, ${users.length}, ${itemCount})
    on conflict (id) do nothing
  `;

  return { skipped: false as const, companies: companies.length, users: users.length, items: itemCount };
}

export const adoptLegacyLogin = createServerFn({ method: "POST" })
  .validator((input: { identifier: string; password: string }) => ({
    identifier: input.identifier.trim().toLowerCase(),
    password: input.password,
  }))
  .handler(async ({ data }) => {
    await importLegacyShop();
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const rows = await sql<{
      username: string;
      email: string;
      django_password: string;
      is_superuser: boolean;
      auth_user_id: string;
    }>`
      select * from legacy_credentials
      where username = ${data.identifier} or email = ${data.identifier}
      limit 1
    `;
    const row = rows[0];
    if (!row) return { ok: false as const };
    const valid = await verifyDjangoPassword(data.password, row.django_password);
    if (!valid) return { ok: false as const };

    const existing = await sql<{ id: string }>`
      select id from "user" where id = ${row.auth_user_id} or lower(email) = ${row.email} limit 1
    `;
    const userId = existing[0]?.id ?? row.auth_user_id;
    if (existing.length === 0) {
      await sql`
        insert into "user" (id, name, email, "emailVerified", "createdAt", "updatedAt")
        values (${userId}, ${row.username}, ${row.email}, true, now(), now())
        on conflict (id) do nothing
      `;
    }
    const hashed = await hashPassword(data.password);
    const accounts = await sql<{ id: string }>`
      select id from "account" where "userId" = ${userId} and "providerId" = 'credential' limit 1
    `;
    if (accounts.length === 0) {
      await sql`
        insert into "account" (
          id, "accountId", "providerId", "userId", password, "createdAt", "updatedAt"
        ) values (
          ${`acc-${userId}`}, ${userId}, 'credential', ${userId}, ${hashed}, now(), now()
        )
      `;
    } else {
      await sql`
        update "account" set password = ${hashed}, "updatedAt" = now()
        where id = ${accounts[0].id}
      `;
    }
    if (row.is_superuser) {
      await sql`
        insert into platform_admins (user_id, email)
        values (${userId}, ${row.email})
        on conflict (user_id) do nothing
      `;
    }
    return { ok: true as const, email: row.email };
  });
