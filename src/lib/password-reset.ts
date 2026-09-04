import { createServerFn } from "@tanstack/react-start";
import { createHash, randomInt } from "node:crypto";
import { hashPassword } from "better-auth/crypto";

function sha256(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

function normalizeEmail(email: string) {
  return email.trim().toLowerCase();
}

export const requestPasswordReset = createServerFn({ method: "POST" })
  .validator((email: string) => normalizeEmail(email))
  .handler(async ({ data: email }) => {
    if (!email.includes("@")) {
      return { ok: true as const, previewCode: null as string | null };
    }
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    await sql`
      create table if not exists password_resets (
        id text primary key,
        email text not null,
        code_hash text not null,
        expires_at timestamptz not null,
        used boolean not null default false,
        created_at timestamptz not null default now()
      )
    `;
    const users = await sql<{ id: string; email: string }>`
      select id, email from "user"
      where lower(trim(email)) = ${email}
      limit 1
    `;
    if (users.length === 0) {
      return { ok: true as const, previewCode: null as string | null };
    }
    const code = String(randomInt(100000, 1000000));
    const id = crypto.randomUUID();
    await sql`
      update password_resets
      set used = true
      where email = ${email} and used = false
    `;
    await sql`
      insert into password_resets (id, email, code_hash, expires_at, used)
      values (${id}, ${email}, ${sha256(code)}, now() + interval '15 minutes', false)
    `;
    return { ok: true as const, previewCode: code };
  });

export const confirmPasswordReset = createServerFn({ method: "POST" })
  .validator((input: { email: string; code: string; password: string }) => ({
    email: normalizeEmail(input.email),
    code: input.code.replace(/\s/g, ""),
    password: input.password,
  }))
  .handler(async ({ data }) => {
    if (data.password.length < 8) {
      return { ok: false as const, error: "Use at least 8 characters." };
    }
    if (!/^\d{6}$/.test(data.code)) {
      return { ok: false as const, error: "Enter the 6-digit code." };
    }
    const { getSql } = await import("@/lib/db");
    const sql = await getSql();
    const rows = await sql<{ id: string }>`
      select id from password_resets
      where email = ${data.email}
        and code_hash = ${sha256(data.code)}
        and used = false
        and expires_at > now()
      order by created_at desc
      limit 1
    `;
    if (rows.length === 0) {
      return { ok: false as const, error: "That code is wrong or has expired." };
    }
    const users = await sql<{ id: string; name: string }>`
      select id, name from "user" where lower(email) = ${data.email} limit 1
    `;
    if (users.length === 0) {
      return { ok: false as const, error: "No account uses that email." };
    }
    const userId = users[0].id;
    const hashed = await hashPassword(data.password);
    const accounts = await sql<{ id: string }>`
      select id from account
      where "userId" = ${userId} and "providerId" = 'credential'
      limit 1
    `;
    if (accounts.length === 0) {
      const accountId = crypto.randomUUID();
      await sql`
        insert into account (
          id, "accountId", "providerId", "userId", password, "createdAt", "updatedAt"
        ) values (
          ${accountId}, ${userId}, 'credential', ${userId}, ${hashed}, now(), now()
        )
      `;
    } else {
      await sql`
        update account
        set password = ${hashed}, "updatedAt" = now()
        where id = ${accounts[0].id}
      `;
    }
    await sql`update password_resets set used = true where id = ${rows[0].id}`;
    return { ok: true as const };
  });
