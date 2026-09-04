# Cloud Stock Manager

New shop app (Inventory + Sell). The previous Django project is kept in `legacy/`.

## Railway

This service must stay on the **same Postgres** the live shop already uses.

Railway reads `railway.json` + `nixpacks.toml`:

- Builder: Nixpacks, **Node 22 only** (Vite 8 will not install on Railway’s Node 20.18)
- Install: `npm ci --include=dev` so Vite/Nitro are present during the image build
- Build: `npm run build`
- Start: `node scripts/start-railway.mjs` (listens on `$PORT`)

Do not point the service at `legacy/`. That folder is the old Django app and is not part of this build.

Existing usernames, emails, passwords, shops, and stock are imported on first boot. Old Django tables are not deleted.
