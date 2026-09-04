# Cloud Stock Manager

New shop app (Inventory + Sell). The previous Django project is kept in `legacy/`.

## Railway

Use the **same Postgres** the live shop already uses.

This repo is set to Nixpacks + Node 22:

- Install: `npm install --include=dev`
- Build: `npm run build`
- Start: `node scripts/start-railway.mjs` on `$PORT`
- Health check: `/healthz`

Optional variables:

- `DATABASE_URL` — existing Railway Postgres
- `BETTER_AUTH_URL` — public https URL (auto-filled from `RAILWAY_PUBLIC_DOMAIN` if unset)
- `BETTER_AUTH_SECRET` — any long random string

Do not set the service root directory to `legacy/`.
