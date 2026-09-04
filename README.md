# Cloud Stock Manager

Shop ledger (inventory + sales). The previous Django project is in `legacy/`.

## Railway

In the service settings:

1. Builder: **Dockerfile** (this repo includes one on Node 22 — the old Node 20 image cannot build Vite 8)
2. Root directory: repo root, not `legacy/`
3. Same Postgres as the live shop (`DATABASE_URL`)

Variables to set:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Existing Railway Postgres |
| `BETTER_AUTH_SECRET` | Long random string |
| `BETTER_AUTH_URL` | Public https URL, e.g. `https://your-app.up.railway.app` |
| `GOOGLE_CLIENT_ID` | Google OAuth client id |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

Google Cloud console → APIs & Services → Credentials → OAuth client (Web):

- Authorized JavaScript origin: `https://your-app.up.railway.app`
- Authorized redirect URI: `https://your-app.up.railway.app/api/auth/callback/google`

People can then create an account or sign in with Google, or with email and password.
