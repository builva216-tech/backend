# V5 API additions

All paths are relative to `/api/v1/`. Authentication and existing role checks apply unless explicitly public.

| Method/path | Purpose |
| --- | --- |
| `POST auth/password-recovery/request/` | Public mobile recovery; `{email}`; 202 with generic message, `challengeId`, expiry and resend seconds. No OTP in the response. |
| `POST auth/password-recovery/confirm/` | Public mobile reset; `{challengeId, code, newPassword}`; 200 on success. |
| `POST admin/auth/password-recovery/request/` | Public admin-only recovery; same request/response shape. |
| `POST admin/auth/password-recovery/confirm/` | Public admin-only reset; same request shape. |
| `GET admin/analytics/?days=7\|30\|90` | Platform business and service metrics, period buckets and queues. |
| `GET admin/accounts/?q=&role=&active=&page=` | Admin account directory; page-size default 20, maximum 100. |
| `PATCH admin/accounts/{userId}/access/` | Admin access change; `{isActive, reason}`. Does not approve agency documents. |
| `GET admin/audit/?page=` | Paginated account/agency decision activity. |
| `GET agencies/crm/records/` | Approved agency's own CRM records connected to its bookings. |
| `GET/PATCH agencies/crm/records/{customerId}/` | Approved agency relationship record. PATCH requires `expectedRevision`, accepts alias, notes, tags and tasks. |
| `GET bookings/agency/{bookingId}/customer-summary/` | Current customer name/city/identity state for an owned booking. No identity documents. |
| `GET bookings/agency/{bookingId}/customer-contact/` | Phone gated by owned booking status. Requested/rejected/cancelled remain locked. |
| `PATCH agencies/me/` | Approved agency profile publishing: agencyName, governorateCode, city, bio, services, optional expectedUpdatedAt; multipart profileImage or JSON removeProfileImage. |

CRM payload example:

```json
{
  "agencyId": "current-agency-user-uuid",
  "expectedRevision": 0,
  "alias": "Airport guest",
  "notes": "Prefers airport collection",
  "tags": ["VIP", "Follow up"],
  "tasks": [{"id": "task-1", "title": "Confirm return time", "due": "2026-10-05", "completed": false}]
}
```

A successful response adds customerId, revision and updatedAt. A stale revision returns 409 with currentRecord; the client requires review before retrying. Limits: alias 80 characters, notes 4,000, at most 100 tasks with unique IDs and valid dates; task titles 160 characters. Valid tags: VIP, Business, Family, Follow up. No contact/identity documents are copied into CRM records.

New clients send agencyId with owner profile/CRM writes and owner queries to prevent a request from an earlier account context mutating another agency after a login change. The backend validates it against the authenticated agency user UUID, not the agency profile UUID. These checks supplement normal ownership restrictions.

Public/current agency profiles now include updatedAt, profileImage and isVerified. Verification is backend-derived and is not a writable profile field. Images accept actual JPEG, PNG or WEBP data up to 2 MB, receive canonical filenames and are served with the correct MIME type. Pending agencies can read their registration profile but cannot edit restricted profile features.

Admin agency list keeps its legacy default behavior. The new admin app sends submittedOnly=true for pending queues; this excludes registered agencies with no document submission. Overview pendingAgencies now counts submitted pending reviews.

Recovery codes expire after 15 minutes, allow five incorrect attempts, and are bound to a challenge/purpose/account/password. Requests have a 60-second per-email cooldown and a five-request hourly cap. Invalid/blocked/wrong-role accounts receive the same public request shape. The supervised `send_password_recovery_emails` worker handles delivery and security notices. Password resets revoke prior sessions without changing agency activation status.
