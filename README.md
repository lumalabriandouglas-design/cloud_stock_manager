# Cloud Stock Manager

Production app is **Django** in `legacy/`. Railway should build the Python Dockerfile.

## What this deploy runs

The live shop: inventory, sell, reports, team, billing, import/export, ledger scan.

Features brought over from the Node experiment:

- Continue with Google
- Forgot password (6-digit code)
- Sign in with username or email
- Invite staff by email (they join on register / Google)
- Today page (today + last 7 days)
- Remove a product that has no sales

## Railway

Builder: **Dockerfile** (this repo). Start command can stay default.

Variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Existing shop Postgres |
| `SECRET_KEY` | Long random string |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.railway.app` |
| `GOOGLE_CLIENT_ID` | Google OAuth (optional) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth (optional) |
| `GEMINI_API_KEY` | Ledger scanner (optional) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP for low-stock mail and subscription reminders |

Google redirect URI: `https://your-app.up.railway.app/accounts/google/callback/`

Subscription reminders are a separate daily Railway cron (`python manage.py send_subscription_reminders`, `0 5 * * *`). See [DEPLOY.md](DEPLOY.md). Do not put that command in the web start command.
