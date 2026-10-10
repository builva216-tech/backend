# Backend — revision 2 entry point

For this complete bundle, start from the parent directory with `py tools/local.py backend`, after preserving/configuring backend/.env.local as described in ../README.md. The runner uses PostgreSQL on PC port 55432, installs dependencies, applies migrations and starts the LAN API. Do not replace an existing database password with an example value.

New notification API and worker: ../NOTIFICATIONS_AND_UPDATES.md. Prepared Django origin/R2: ../CLOUDFLARE_R2.md. R2 stores files and cannot execute Django. The internal backend documentation below is retained for reference; the parent README is the current bundle workflow.

---

> Revised bundle: start with the root `README.md` / `START_HERE_AR.md`. Root `CLOUDFLARE_R2.md`, `ANDROID_RELEASE.md` and `VALIDATION.md` supersede older setup/release instructions below.

# CarRent TN Backend — V5 update

See the bundle `INSTALL.md` for coordinated installation and SMTP/worker setup. See [V5_API.md](V5_API.md) for new endpoints. The older foundation notes below are retained for context.

# CarRent TN Backend

Initial backend foundation for the CarRent TN Customer/Agency Flutter application.

## Included in this phase

- Django + Django REST Framework
- PostgreSQL
- Custom UUID user model with `customer`, `agency`, and `admin` roles
- JWT access/refresh tokens
- Mobile auth endpoint that rejects admin/staff sessions
- Customer registration
- Agency registration with canonical `governorateCode` + optional `city`
- Django Admin for MVP administration
- Tunisia governorates API using the same JSON field names as the Flutter model
- 24-governorate seed command
- Basic role permission classes
- Health endpoint
- Tests for auth and locations contracts

## API v1 endpoints

- `GET /api/v1/health/`
- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`
- `POST /api/v1/auth/register/customer/`
- `POST /api/v1/auth/register/agency/`
- `GET /api/v1/auth/me/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/locations/governorates/`
- `/admin/` for Django Admin

The successful login/registration response intentionally matches the current
Flutter `AuthSessionModel` contract:

```json
{
  "user": {
    "id": "uuid",
    "fullName": "Name",
    "email": "user@example.com",
    "phone": "+216...",
    "role": "customer",
    "accountStatus": "active",
    "isEmailVerified": false
  },
  "accessToken": "...",
  "refreshToken": "..."
}
```

The governorates endpoint also matches the current Flutter model:

```json
[
  {
    "code": "TN-11",
    "nameAr": "تونس",
    "nameFr": "Tunis",
    "nameEn": "Tunis"
  }
]
```

## Windows setup

### 1. Create the project directory

Extract this project to a location such as:

```powershell
C:\devlopment\carrent_tn_backend
```

### 2. Start PostgreSQL

Docker Desktop must be running:

```powershell
docker compose up -d db
```

### 3. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\dev.txt
```

### 4. Create local environment variables

```powershell
Copy-Item .env.example .env
```

Change `DJANGO_SECRET_KEY` in `.env`.

### 5. Create initial migrations

These commands are intentionally run after the custom user model exists and
before the first database migration:

```powershell
python manage.py makemigrations accounts locations agencies
python manage.py migrate
```

### 6. Seed Tunisia governorates

```powershell
python manage.py seed_tunisia_governorates
```

### 7. Create the internal MVP admin

```powershell
python manage.py createsuperuser
```

Django will request the required user fields.

### 8. Run checks and tests

```powershell
python manage.py check
python manage.py test
```

### 9. Run the API

```powershell
python manage.py runserver 0.0.0.0:8000
```

Then test:

```text
http://127.0.0.1:8000/api/v1/health/
http://127.0.0.1:8000/api/v1/locations/governorates/
http://127.0.0.1:8000/admin/
```

## Important security boundary

The Customer/Agency mobile auth endpoint explicitly rejects `admin` and
`is_staff` accounts. Django Admin uses Django's session authentication and is
separate from the mobile JWT flow.

Future admin APIs should live under a separate `/api/v1/admin/...` namespace
and enforce server-side staff/admin permissions. Flutter Desktop is not the
security boundary; Django permissions are.
