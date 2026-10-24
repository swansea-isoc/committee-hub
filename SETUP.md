# Private activation — keep the discount sites untouched

## 1. Dedicated backend

Create/connect a dedicated Supabase project for the committee hub. Applying this code to a project, enabling a provider, or entering account credentials requires the project owner's authorisation; publishing to GitHub does none of these things automatically.

Apply `server/schema.sql` to that NEW project once. No real records are seeded. Keep both `committee-files` and `committee-receipts` private and do not add public storage policies.

Deploy `server/index.ts` and `server/policy.mjs` as an Edge Function named `committee-api`. Set `verify_jwt=false` for this function because it validates Google tokens with `auth.getUser()` itself and accepts separate secret-protected agent routes. Never remove those validation paths. A disabled platform JWT pre-check is **not** anonymous application access.

## 2. Private configuration

Use `server/.env.example` as a list of secret NAMES. Do not commit filled-in credentials.

- Set `OWNER_EMAIL` to the initial administrator's confirmed Google email (provided separately in the private handover), and `OWNER_NAME` to their name.
- Keep `OWNER_ONLY=true` while the administrator tests. This denies all other accounts even if they have been added to the allowlist.
- Set independent cryptographically random `RATE_LIMIT_SECRET`, `EMAIL_AGENT_SECRET`, and `MEDIA_IMPORT_SECRET` values (at least 32 characters each).
- Generate `FINANCE_ENCRYPTION_KEY` as 32 random bytes in base64. Keep a secure backup; losing it makes stored bank details unreadable. Do not enable financial record collection without a backup/recovery plan.
- Keep `EMAIL_ENABLED=false` and `MEDIA_IMPORT_ENABLED=false` until their actual end-to-end tests have passed.
- Set `HUB_URL=https://swansea-isoc.github.io/committee-hub/` and `HUB_ORIGINS=https://swansea-isoc.github.io`.
- Supabase supplies its server URL and service-role key to the function. The service-role key must never appear in browser files.

The owner account can be bootstrapped on their first verified Google sign-in if and only if the membership table is empty. Alternatively insert the owner securely before enabling the optional before-user-created hook. Never turn on that hook before the owner is pre-approved, or it will block the first login.

## 3. Google sign-in

Configure the Google provider in Supabase using a Google Cloud OAuth client owned by the society/authorised administrator. Use the exact Supabase callback URL shown in its provider settings. In Supabase Auth URL settings allow the hub's exact production URL. Use a dedicated client; do not reuse the discount directory.

Then set only the project URL and **publishable/anon browser key** in `site/config.js`. Leave all other secrets on the backend. Restrict Google provider scopes to basic sign-in unless a later integration needs more; calendar-add links do not need calendar write permission.

Sign in as the owner. Confirm an unapproved Google account is rejected. Confirm the owner session restores on refresh and explicit sign-out clears the workspace. New members are added under Settings → Approve an email. Change `OWNER_ONLY` to `false` only when the owner is ready to admit other approved members.

## 4. Mail from the ISOC Google account

In a NEW Apps Script project under the account that should send committee emails, paste `server/agent.gs`. Do not replace the existing media automation.

In Script Properties set `HUB_API_URL` to `https://PROJECT.supabase.co/functions/v1/committee-api` and `EMAIL_AGENT_SECRET` to the corresponding server secret. Authorise `installEmailAgent()` as the ISOC account. It installs a five-minute time trigger; it does not open the user's inbox. Review authorisation scopes before accepting.

While `OWNER_ONLY=true`, enable `EMAIL_ENABLED=true`, assign an action to the owner, and test the assignment message. Test one reminder, task completion, a media request and a claim status change with test data. Ensure sent mail is acknowledged. The agent checks daily recipient quota; it cannot guarantee instantaneous delivery or delivery to the inbox. If MailApp succeeded but acknowledgement failed, do not blindly resend: check the mailbox, then resolve that job manually. `sending` jobs older than 30 minutes become `failed` for review.

Finances and well-being content are never placed in notification emails. Recipient access is rechecked just before handing each job to the mail agent. Revocation and completion cancel queued work where appropriate. There is no global shared password.

## 5. Existing media form and tracker

Add the original form and sheet URLs under workspace Settings. The established live links are in the private handover, not hard-coded in public browser source.

Native hub requests already use the hub database once activated. To also import future Google Form responses, use the same NEW Apps Script companion, set `MEDIA_FORM_ID`, `MEDIA_IMPORT_SECRET`, and the exact `MEDIA_DEADLINE_QUESTION`. Optional question-title overrides are documented in `agent.gs`. Inspect an actual form response and map its date type; do not guess ambiguous UK/US dates.

Run `installMediaImport()`, submit one labelled test response, and verify that it appears exactly once in the hub AND that the original sheet/calendar automation still works. Then set `MEDIA_IMPORT_ENABLED=true`. This is a one-way import of new submissions, not a historical migration and not a two-way sheet/status sync. A name typed in a form is not enough to bind that request to an authenticated account.

## 6. Records and private files

Do not import the uploaded Excel snapshot automatically. First complete a privacy/retention review and verify access with a non-finance executive. Only Abubakr and Fadumo should receive `finance=true`; the president and other execs do not get it by default. The owner must explicitly assign the correct president-only inbox recipient before that route accepts messages.

Test: small PDF/image receipt; nested folder; drag/drop; invalid file type; oversized file; unrelated member receipt denial; revoked member access denial; receipt download; cash claim marked Paid only AFTER an actual bank payment. Uploaded files are limited to 20 MB; signed upload links expire at the storage provider's default lifetime, downloads after 60 seconds. Antivirus scanning is not included. Clean abandoned `uploading` rows/objects after an agreed interval, and apply retention to reviewed feedback, notifications and finance records.

## 7. Launch checklist

- [ ] Apply migration successfully to dedicated Supabase project.
- [ ] Configure Google OAuth and allowed redirect URL.
- [ ] Test owner session and deny an unapproved account.
- [ ] Validate role/access boundaries against the live API (not just browser tests).
- [ ] Verify private storage and encrypted reimbursement round-trip.
- [ ] Authorise ISOC mail agent and receive real owner-only test emails.
- [ ] Verify reminders while browser is closed; stop them on completion/reassignment.
- [ ] Set president/finance/media recipients; verify confidential inbox routing.
- [ ] Keep old Forms/Sheets/ClickUp/OneDrive untouched until an explicit transition is agreed.
- [ ] Only then switch OWNER_ONLY off and invite approved committee members.

## Primary documentation

- Google OAuth: https://supabase.com/docs/guides/auth/social-login/auth-google
- Storage access: https://supabase.com/docs/guides/storage/security/access-control
- Google email sending: https://developers.google.com/apps-script/reference/mail/mail-app
- Installable triggers: https://developers.google.com/apps-script/guides/triggers/installable
- Google service quotas: https://developers.google.com/apps-script/guides/services/quotas
