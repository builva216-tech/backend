> V5: use the coordinated bundle INSTALL.md and V5_API.md first. These older setup notes are retained as historical context.

# CarRent TN — Django Auth Readiness Update

This patch prepares Django for the upcoming Flutter JWT migration without
breaking the existing customer contact-change flow.

## Added

- Server-side customer email/phone OTP challenge
- Hashed OTP storage (the raw code is never stored)
- 5-minute OTP validity
- 60-second resend delay
- 5 incorrect-attempt limit
- `prototypeOtpCode` returned only while `DEBUG=True`
- Current agency profile endpoint
- Django Admin read-only view for contact verification challenges
- Tests

## API added

```text
POST /api/v1/auth/contact/change/request/
POST /api/v1/auth/contact/change/confirm/
GET  /api/v1/agencies/me/
```

## Apply

Copy the patch files over the backend project, then:

```powershell
cd C:\devlopment\carrent_tn_backend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python manage.py check
python manage.py migrate
python manage.py test
```

`0002_contactverificationchallenge.py` is included, so do not run
`makemigrations` for this patch unless Django reports model changes that are
not represented by the migration.

Then run:

```powershell
python manage.py runserver 0.0.0.0:8000
```

## Important

`prototypeOtpCode` is intentionally exposed only in local DEBUG mode so the
current Flutter prototype can be tested without an SMS/email provider.
Production settings have `DEBUG=False`, so the raw OTP is not returned.

The next migration step will connect an SMS/email provider and remove the
development-only on-screen OTP.
