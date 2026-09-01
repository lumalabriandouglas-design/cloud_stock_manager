# Cloud Stock Manager

A multi-tenant inventory & stock management system built with Django.
Designed for small-to-medium businesses (especially in Uganda – UGX currency).

Features:
- Multi-company isolation (each user belongs to one company)
- Product / Category management
- Stock In & Sales recording
- Low stock alerts
- Today's sales & inventory value dashboard
- **AI Ledger Scanner** – upload a photo of a handwritten stock book and Gemini extracts the items automatically
- Clean Tailwind CSS dashboard

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

> Get a free Gemini API key at https://aistudio.google.com/apikey

### 3. Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Create a Company + Link User (important!)

1. Go to http://127.0.0.1:8000/admin/
2. Create a **Company**
3. Create a **UserProfile** and link your superuser (or any user) to that company

Without a UserProfile the dashboard will crash.

### 5. Run

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/ → login with the user that has a profile.

---

## Project Structure

```
cloud_stock_manager/
├── core/                 # Django project settings & urls
├── inventory/            # Main app
│   ├── models.py         # Company, UserProfile, Category, Item, Sale, StockIn
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

## Key Models

| Model        | Purpose                                      |
|--------------|----------------------------------------------|
| Company      | Tenant / business                            |
| UserProfile  | Links Django User → Company                  |
| Category     | Product categories (per company)             |
| Item         | Products with buy/sell price & stock qty     |
| Sale         | Sales records (auto-deducts stock)           |
| StockIn      | Stock receipt records                        |

---

## AI Ledger Scanner

Upload a photo of a handwritten stock ledger. The system uses Google Gemini to extract:

- Product name
- Buy price
- Sell price
- Quantity

Items are automatically created or updated in your inventory.

---

## Production Notes

- Set `DEBUG=False`
- Use a strong `SECRET_KEY`
- Set proper `ALLOWED_HOSTS`
- Switch to PostgreSQL / MySQL
- Collect static files (`python manage.py collectstatic`)
- Use a proper email backend
- Put the app behind HTTPS

---

## License

MIT (feel free to change)
