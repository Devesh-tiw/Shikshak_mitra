# Shikshak Mitra

A simple, mobile-first attendance website for Amrita Vishwa Vidyapeetham teachers. Every teacher signs in with their own Google account and starts with an empty workspace — **no sample classes, sample students, or demo data are included.**

## Main features

- Tap-based mobile attendance register: tap a student once for Present, again for Late, then Absent.
- Teacher-created classes: custom class name, programme/branch, admission batch, section and student count.
- Branches included: AIE, CSE, CCE, AIDS, QC and ECE, plus a custom option.
- Automatic Amrita-style roll-number generation when a student is created.
- Editable student roster.
- SQL attendance records saved by class, date and slot.
- WhatsApp attendance-summary sharing.
- Excel `.xlsx` attendance export with session dates, slots and per-student percentage.
- Per-class insights: classes taken, overall attendance, trend chart and students below 75%.
- Teaching plan for tests, assignments and reminders.

## Project structure

```text
shikshak_mitra/
├── manage.py
├── requirements.txt
├── config/                 # Django project settings and URLs
└── academy/                # Attendance application
    ├── models.py
    ├── views.py
    ├── forms.py
    ├── templates/academy/
    └── static/academy/
```

## Local setup

```bash
cd shikshak_mitra
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Google Sign-In setup

Google authentication requires your own Google Cloud OAuth credentials. There is intentionally no demo-login fallback.

1. In Google Cloud Console, create an OAuth 2.0 **Web application** client.
2. Add your callback URL, for example:
   `http://127.0.0.1:8000/auth/google/callback/`
3. Set environment variables before running Django:

```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/auth/google/callback/"
export DJANGO_SECRET_KEY="use-a-long-random-value-in-production"
```

After Google login, each teacher only sees their own classes and student records.

## Production database

The project uses SQLite for local development. For a multi-teacher campus deployment, configure PostgreSQL and use HTTPS, secure cookies, strict allowed hosts, and a production secret key.
