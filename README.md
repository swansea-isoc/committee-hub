# Swansea ISOC committee hub — main application

**Main entry:** https://swansea-isoc.github.io/committee-hub/

This is the new dark-blue application source, not an automatically activated private service. `demo.html` now redirects to the main sign-in page. There are **no sample accounts, task fixtures, role switches or preview mode in the published application**.

## Current state

The interface can be published independently. Google sign-in, records, uploads, reminders and email delivery require the dedicated private Supabase backend plus the ISOC Google-account mail agent. With blank `site/config.js` settings, the website deliberately denies workspace access. This is not a password screen pretending to protect a public data file.

Nothing in this project changes `swansea-isoc/isoc-discounts` or `abubakrmajid1/isoc-discounts`.

## Features in the application code

- My Space: a personal greeting, own action points, and media/expense/well-being shortcuts.
- Red = overdue or blocked; amber = due within seven days or for review; blue = in progress; green = complete. Labels accompany colour.
- Executives assign actions; members see and update their own. Changes use revisions to prevent overwriting concurrent work.
- Per-person one-off, before-deadline, 24-hour and 7-day recurring reminders. Completing or reassigning an action stops its old reminders. The assigning executive receives completion notifications.
- Native media requests and team status updates; existing Google Form may be embedded, with an optional one-way form-import bridge.
- One-click Google Calendar event creation. This is **not automatic two-way calendar synchronisation**; changes need updating in Calendar manually.
- Native reimbursement claims with receipt upload, encrypted payment details and a separately authorised Gen Sec finance desk. No actual bank payments are initiated.
- Private shared folders, multiple file upload / drag-and-drop, image preview, download and delete. This is a **new file library**, not an automatic OneDrive mirror.
- Anonymous-to-recipient well-being messages; president-only inbox remains separate from general exec access. Email contains only a generic alert and authenticated hub link.
- Administrator-managed approved Google accounts. Initial deployment is owner-only; other emails can be approved without immediately opening the hub to everyone.

## Source files

`site/` is the only published directory. `server/` contains the private API, migration and mail/import agent. `tools/` contains tests with synthetic data. Tests are **not loaded into the website**.

The public repository contains no actual allowlist, passwords, finance rows, uploaded receipts, membership emails or API secrets. A supplied public ISOC logo is reused. No font files are distributed.

## Activate the private services

See [SETUP.md](./SETUP.md). Do not enter personal/finance records until the activation checks pass. `server/schema.sql` targets a new dedicated Supabase project and uses `hub3_` table names; do not apply it blindly to an unrelated database.

All browser database access is denied. The Edge API verifies Google identities and checks active membership and roles for every operation. Storage buckets are private; uploads/downloads use short-lived scoped URLs. Reimbursements are encrypted with a server-only AES-GCM key; finance permission does not follow executive/admin status automatically.

Email sending uses an optional Apps Script `MailApp` agent authorised as the ISOC Google account. It checks the remaining daily quota, claims jobs atomically, and will not automatically resend a message with an ambiguous delivery acknowledgement. Failed/uncertain jobs need mailbox review. Emails have not been activated by publishing the web files.

## Test scope

- Node tests cover access decisions, input validation, reminder timing, permitted uploads and bank-field shape.
- Browser tests replace auth/API responses with test doubles. They test interfaces and API payloads, not actual Google consent or email delivery.
- PostgreSQL CI applies the migration in a disposable database, verifies grants/RLS flags, task notification triggers, revision conflicts, reminder cancellation, recipient routing and email leases. The `storage.buckets` scaffold in CI is not a substitute for testing Supabase Storage after activation.

## Known integration boundaries

ClickUp is not read, written, migrated or synchronised. Native hub actions are separate until the committee explicitly approves a migration. Existing Google Forms/Sheets and OneDrive are not modified. The Google Form import is opt-in, one-way, and requires matching the original form's exact question titles and date format. Existing forms remain usable separately.

Private messages are anonymous **to recipients**, not guaranteed anonymous to infrastructure administrators. Authentication/hosting logs may be linkable. Set an agreed retention policy, monitor storage/mail quotas, and review security before inviting the full committee. No antivirus scanning is provided for uploaded documents.
