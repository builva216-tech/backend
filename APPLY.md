> V5: use the coordinated bundle INSTALL.md and V5_API.md first. These older setup notes are retained as historical context.

# Django — Public Agency Profile bridge

Copy this patch over:

```text
C:\devlopment\carrent_tn_backend
```

No migration is required.

Then run:

```powershell
cd C:\devlopment\carrent_tn_backend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python manage.py check
python manage.py makemigrations --check
python manage.py test
```

New endpoint:

```text
GET /api/v1/agencies/{agencyUserId}/public/
```

Only an approved + active agency is returned.

The response intentionally excludes:

```text
email
phone
responsible person
```

because this endpoint is public-facing.

Current response includes the safe base profile:

```text
agencyId
displayName
governorateCode
governorate names
city
bio = ""
services = []
updatedAt
```

`bio` and `services` remain empty until the agency public-profile editing
feature itself is migrated from local prototype storage to Django.
