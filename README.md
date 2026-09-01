# Cloud Stock Manager

Multi-tenant cloud inventory / stock management system for small businesses.

## Features

- Multi-company isolation
- Owner-controlled staff permissions
- Stock in / sales / categories
- AI handwritten ledger scanner (Gemini)
- Sales reports + CSV export
- Low-stock alerts (dashboard + optional email)
- Clean professional UI

## Local development

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # edit SECRET_KEY etc.
python manage.py migrate
python manage.py createsuperuser   # optional platform admin
python manage.py runserver
```

Open http://127.0.0.1:8000/

- Register a new business at `/register/`
- Or login and create a company at `/setup/`

## Deploy on Railway

### 1. Create project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. **New Project** → **Deploy from GitHub repo** → select `cloud_stock_manager`
3. Railway will detect Python and start building

### 2. Add PostgreSQL

1. In the project → **New** → **Database** → **PostgreSQL**
2. Railway automatically sets `DATABASE_URL` for your web service

### 3. Environment variables

In the **web service** → **Variables**, add:

| Variable | Value |
|----------|--------|
| `SECRET_KEY` | Generate a long random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.railway.app` (or your custom domain later) |
| `GEMINI_API_KEY` | (optional) your Google AI key for the scanner |

`DATABASE_URL` is injected automatically by the PostgreSQL plugin — do **not** set it manually.

### 4. Deploy commands

Railway usually auto-detects Django. If needed, set:

- **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command**: `gunicorn core.wsgi --log-file -`

Or rely on the `Procfile`.

### 5. Run migrations

After the first deploy, open the service → **Settings** or use Railway CLI / one-off command:

```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

(Or add a release command in Railway that runs `python manage.py migrate`.)

### 6. Done

Open the public Railway URL. Register a business or login as superuser and use Platform Admin to create businesses.

---

## Notes

- **Media files** (ledger photos) are stored on the local disk. On Railway the filesystem is ephemeral — for production AI scans you should later move media to S3/Cloudinary. For MVP it is acceptable.
- **Email**: set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` when you want real low-stock emails.
- Locally the app still uses SQLite if `DATABASE_URL` is not set.
