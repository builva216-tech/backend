# CarRent TN Blitz backend update

Deploy the contents of this folder to your existing carrent-blitz GitHub repository. Use the root Dockerfile, port 8000 and start command web. Keep the existing PostgreSQL DATABASE_URL, DJANGO_SECRET_KEY, hostnames and browser CORS origins.

After rebuilding, run release against the same database before using the updated apps. It applies committed migrations, seeds governorates and preserves any referenced local uploads still present. If temporarily using release as Start command, restore web after its successful exit. Do not create a new database or another admin account.

Keep /app/media as a persistent folder for legacy files and videos over 10 MB. Small uploads are archived in the existing PostgreSQL database by default on Blitz; private R2 remains supported. Lost old files require resubmission. No public /media route is exposed.

Read HOSTED_UPDATE.md for deployment steps, SMTP settings, admin plan editing, bug reports, client rebuilds and validation limits. The same document is in the full app ZIP.
