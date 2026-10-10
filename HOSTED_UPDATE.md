# Hosted fixes and admin plans — 10 October 2026

This source update addresses hosted file previews, agency review, bug reports, and editable membership offers. Both clients use https://carrent-blitz.builva.blitz.cloud/api/v1/ and are version 1.0.3+4. The ZIP contains source, not built APKs. No GitHub commit, live deployment, database change, or real email has been made here.

## 1. Update the server repository

Use the separate CarRent_Blitz_Deployment.zip for your existing private carrent-blitz GitHub repository. Extract it, then copy the CONTENTS of its carrent-blitz folder into your repository folder. The same files are under backend in the full source ZIP. Keep your existing .git folder, secrets, and Blitz database. Commit and push the backend changes from VS Code. Include all new apps/core/migrations and apps/agencies/migrations files, hosting/gunicorn_conf.py, root Dockerfile, and blitz-entrypoint.sh.

This is required: the hosted server returned HTTP 404 for POST /api/v1/support/bug-reports/ during diagnosis. Updating Flutter alone cannot install the backend endpoint.

Keep these Blitz settings:

- Port: 8000.
- Start command: web (remove previous createsuperuser/background-shell overrides).
- DJANGO_SETTINGS_MODULE: config.settings.blitz (also set by the Dockerfile).
- Existing DATABASE_URL and DJANGO_SECRET_KEY.
- Existing DJANGO_ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS.
- CORS_ALLOWED_ORIGINS containing http://localhost:7357,http://localhost:7358 and your actual deployed web origins.
- Persistent folder /app/media, writable by UID 1000, for existing files and large videos. Do not expose this folder publicly.

## 2. Apply the included database migrations

The update adds the small-upload archive, saved bug reports, and editable plans. Existing users, administrators, agencies and bookings are retained. Defaults are Small 49 TND, Medium 99 TND, Enterprise 199 TND; migration seeds these once and will not overwrite later edits.

Run the image's release command using the same connected PostgreSQL database before routing traffic to the new version. If Blitz has no before-deploy step/shell for this app, after its new image is built temporarily set Start command to release, restart and wait for Logs to show successful migrations, governorate seeding, and the upload preservation summary. Then restore Start command to web and restart.

The release command executes:

```sh
python manage.py migrate --noinput
python manage.py seed_tunisia_governorates
python manage.py preserve_local_uploads
```

An exit after successful release is expected; release is not a web server. If the earlier PostgreSQL "server closed the connection unexpectedly" error returns, migrations have NOT completed. Resolve that connection failure before using the new pages. Do not recreate the database or create a second administrator.

## 3. Files and agency approval

On Blitz, with R2_ENABLED=false, documents and images up to 10 MB are now saved in PostgreSQL and survive container rebuilds. They are served only through authorized per-record endpoints; there is no public /media directory. The Django Admin file links also require admin authentication. R2_ENABLED=true preserves your existing private R2 storage configuration instead.

The release step copies referenced, still-existing local uploads up to 10 MB into the archive without deleting originals. Uploads already lost before this update cannot be recovered from source code. Larger files stay in /app/media, which must remain a kept folder. Database uploads consume database storage; use private R2 for a growing media library. The migrate_media_to_r2 command now includes both local files and durable uploads; copy and verify them before enabling R2. DURABLE_UPLOADS_ENABLED=false opts back into filesystem storage; do not switch an existing archive off without first transferring its files.

Binary file endpoints accept image/* and application/pdf rather than failing JSON content negotiation. Missing files return a clear 404; unavailable storage returns 503. Photos use their actual MIME type instead of always image/jpeg.

In Admin > Agency verification, open the application and review its five documents. PDFs now render inside the app, with Expand PDF for a larger viewer. If files are missing, use Reject with a reason asking for new uploads. The agency can then resubmit all five files; reload the application and approve once they load and have been reviewed. Approval stays blocked for missing files, including direct API calls. Rejection remains available for pending submissions with missing files.

## 4. Bug reports and email

Reports are saved immediately in the database. The user receives a saved-report confirmation, independent of SMTP availability. Admin > Bug reports shows the report, reporter, reproduction steps, app version, platform, resolution state and email status. Admins can mark reports resolved/reopen them and retry unsent email.

The Blitz web entrypoint now loads hosting/gunicorn_conf.py, which starts a small email-delivery thread in each Gunicorn worker. It retries saved reports and sends only to builva.216@gmail.com, using the authenticated reporter's email as Reply-To. Database locks prevent two live workers from processing the same report simultaneously. Email is at least once: a crash after SMTP accepts a message but before its database update can produce a duplicate with the same report ID. After ten failed attempts, email is marked failed; the saved report remains in the admin inbox and can be retried after correcting SMTP.

In Blitz Environment, configure your SMTP provider. For your Gmail sender:

| Variable | Value |
| --- | --- |
| EMAIL_BACKEND | django.core.mail.backends.smtp.EmailBackend |
| EMAIL_HOST | smtp.gmail.com |
| EMAIL_PORT | 587 |
| EMAIL_HOST_USER | builva.216@gmail.com |
| EMAIL_HOST_PASSWORD | Your Google App Password |
| EMAIL_USE_TLS | true |
| EMAIL_USE_SSL | false |
| EMAIL_TIMEOUT | 10 |
| DEFAULT_FROM_EMAIL | CarRent TN <builva.216@gmail.com> |

Use a Google App Password with 2-Step Verification if your account supports it, or an SMTP provider with a verified sender. Keep these credentials in Blitz. Restart after changing them. SMTP acceptance does not guarantee inbox placement; check Inbox and Spam. When SMTP is unavailable, reports remain saved with queued/failed email status. No real test email was sent during source validation.

Submission requires sign-in and is limited to 5 reports per user/hour and 10 per IP/hour. Keep WEB_CONCURRENCY=1 unless shared CACHE_URL is configured. The existing password-recovery and push workflows retain their separate mail/push commands; this update's in-process worker handles bug-report notifications only.

## 5. Edit membership plans

Open Admin > Plans & prices. Edit each existing tier's name, numeric monthly TND price, optional displayed price text, description, vehicle limit, branch limit, availability and recommended flag. Leave price text blank to show the numeric monthly amount automatically. The three stable plan identifiers are retained for existing subscriptions. The Django /admin/ also exposes Subscription plans.

Agency Membership & branches reads this catalog from the server. Refresh that page after an admin edit; no app rebuild is needed for future price or text changes. Changes to limits affect current subscriptions and trial limits (trial uses Medium), while existing records remain readable. Hiding a plan prevents new requests without deleting existing subscriptions. Edits use a revision check to avoid overwriting another administrator's work. This feature edits your plan catalog; it does not charge cards or automatically activate payments.

## 6. Rebuild/restart both Flutter clients

Extract the full CarRent_TN_Hosted_Update.zip into a fresh folder. Preserve any private signing/Firebase files from your own project. From the extracted folder containing tools:

```powershell
py tools/local.py prepare --app carrent_tn
py tools/local.py prepare --app carrent_tn_admin
py tools/hosted.py --app carrent_tn --device chrome --web-port 7357
```

In another terminal:

```powershell
py tools/hosted.py --app carrent_tn_admin --device chrome --web-port 7358
```

Stop the previous Flutter runs first. Admin has a new PDF dependency; flutter pub get (part of prepare) must update pubspec.lock. The PDF viewer version matches the project's Dart >=3.3 and Flutter >=3.19 requirements. Windows builds require Developer Mode for plugin symlinks. If your admin folder has no windows target yet, run flutter create --platforms=windows . inside carrent_tn_admin once, then return to the bundle root and run py tools/hosted.py --app carrent_tn_admin --device windows.

For a phone, replace chrome with its flutter devices ID. For APKs, from each client folder:

```powershell
flutter build apk --debug --dart-define-from-file=config/production.json
```

Reinstall newly built APKs. Future plan edits happen on the server, but this initial app update requires rebuilt clients. Hosted testing does not require your local Docker container to stay open.

## Validation

114 backend tests passed with an isolated SQLite test database and in-memory email. Checks cover durable PDF/image downloads after an empty-media-folder restart, CORS, authentication, missing-file rejection/resubmission and approval, saved reports, SMTP failures/retries, admin-only catalog edits, stale edits, capacity changes and disabled-plan requests. Two additional R2 copy tests passed, checking archive/local transfers and safe dry runs. Blitz settings and migration consistency checks passed; all 533 Dart source/test files parsed without syntax errors. Flutter SDK is unavailable here, so Flutter analyzer, plugin builds and widget tests must run through prepare on your computer. Hosted database migrations, actual uploads, SMTP delivery, and Windows/Android/browser rendering remain deployment checks.

Official references:
- https://blitz.cloud/docs/settings-and-files/
- https://docs.djangoproject.com/en/5.2/howto/custom-file-storage/
- https://docs.djangoproject.com/en/5.2/topics/email/
- https://pub.dev/packages/pdfrx/versions/1.0.101
