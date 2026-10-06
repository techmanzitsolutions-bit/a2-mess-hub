# TECH MANZ Server Consolidation

This branch is the protected workspace for migrating the **current deployed A2 MESS HUB** to the TECH MANZ server backend.

## Source of truth

The production GitHub Pages app is **generated**, not simply served from raw `www/app.html`.

The deployment workflow `.github/workflows/trigger-stable.yml` prepares the PWA and applies the ordered production patch chain before deployment. That generated output is the functional/UI baseline for migration.

## Migration contract

- Preserve current generated live UI and behavior.
- Preserve Admin, Chef and Member role behavior.
- Preserve month-specific AED 100/200/250 plans and future-month Add Plan flow.
- Preserve receivables, payment/advance, carry-forward, monthly closing and join-date proration.
- Preserve meal skip, kitchen counts, cutoff rules and notifications.
- Preserve inventory, expenses, bill viewing/storage, reports and WhatsApp actions.
- Preserve current V5/V6 UI and approved TM Solutions branding.
- Replace Firebase Authentication with TECH MANZ authentication.
- Replace Firestore with TECH MANZ PostgreSQL/API.
- Replace external bill-image storage with TECH MANZ local storage.
- Reuse the already-built TECH MANZ backend modules where their contracts match.
- Keep `main`, current GitHub Pages and production Firebase untouched until parity validation and acceptance are complete.

## Completion gate

Cutover is allowed only after consolidated Admin/Chef/Member acceptance, finance reconciliation, storage verification, account lifecycle testing, and production-data migration/reconciliation.
