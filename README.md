# Cloud Stock Manager

A multi-tenant inventory & stock management system built with Django.
Designed for small-to-medium businesses (especially in Uganda – UGX currency).

You (the platform owner) can host this for **many different businesses**.  
Each business gets its own isolated data.

---

## Roles & Permissions

| Role                    | Who is this?                          | What they can do                                      |
|-------------------------|---------------------------------------|-------------------------------------------------------|
| **Platform Admin**      | You (superuser)                       | Full access via `/admin/`. Create/delete any company, any user, view everything across all businesses. |
| **Company Owner**       | The person who creates a company      | Full control **inside their own company only**: add products, record sales, scan ledgers, manage stock. |
| **Company Staff**       | Future – employees of a company       | Currently same as Owner (we can restrict later).      |

### Important rules for you as Platform Admin

- You create the Django superuser (`createsuperuser`).
- You can log into `/admin/` and see **all** companies and data.
- Normal business owners **cannot** access `/admin/` unless you give them staff/superuser status (you should almost never do this).
- Business owners only see their own company’s data on the main dashboard.
- When a new user signs up and has no company yet, they are taken to a simple “Create your company” page and automatically become the **Owner** of that company.

---

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/lumalabriandouglas-design/cloud_stock_manager.git
cd cloud_stock_manager

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GEMINI_API_KEY=your-google-gemini-api-key   # optional but needed for ledger scanning
```

### 3. Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run

```bash
python manage.py runserver
```

### 5. First login flow

1. Go to http://127.0.0.1:8000/
2. Log in with the superuser (or any user you create).
3. You will be taken to **“Create your company”** page.
4. Enter a business name → you become the Owner and land on the dashboard.

(You can still use `/admin/` at any time as Platform Admin.)

---

## Features

- Multi-company isolation (each user belongs to one company)
- Product / Category management
- Stock In & Sales recording
- Low stock alerts
- Today's sales & inventory value dashboard
- **AI Ledger Scanner** – upload a photo of a handwritten stock book and Gemini extracts the items
- Clean Tailwind CSS dashboard
- First-time company setup flow

---

## Project Structure

```
cloud_stock_manager/
├── core/                 # Django project settings & urls
├── inventory/            # Main app
│   ├── models.py
│   ├── views.py
│   ├── admin.py
│   ├── templates/
│   └── migrations/
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Production Notes

- Set `DEBUG=False`
- Use a strong `SECRET_KEY`
- Set proper `ALLOWED_HOSTS`
- Switch to PostgreSQL
- Collect static files
- Put the app behind HTTPS

---

## License

MIT
