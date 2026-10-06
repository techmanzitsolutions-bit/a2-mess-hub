# A2 MESS HUB — Live-to-TECH MANZ parity map

Generated-live baseline: `migration/generated-live/app.html` from the exact GitHub Pages patch chain.

Server baseline captured 2026-09-26 from `techmanz-server`:
- FastAPI 0.1.0
- PostgreSQL `a2mess_staging`
- API :3100
- staging web :3200

## Migration principle

Preserve the current generated live UI/UX and workflows. Replace Firebase Auth, Firestore, Firebase Messaging, Cloudinary and Uploadcare underneath with TECH MANZ FastAPI, PostgreSQL and local storage. GitHub is not a runtime dependency after cutover.

## Exact generated-live collections

- system/config
- users
- members
- payments
- expenses
- meals
- mealSkips
- inventory
- monthlyClosings
- pushTokens

## Parity map

| Domain | Generated live behavior / fields | Existing TECH MANZ server | Migration action |
|---|---|---|---|
| Authentication | Firebase email/password, auth state, role profile, disable/remove | JWT login, managed users, active flag | Replace Firebase auth with JWT compatibility adapter; preserve role/disable behavior |
| Users | name,email,role,memberId,active,createdBy; create/edit/disable/remove; member link | Managed users + member relation via `members.user_id` | Add compatibility responses/actions for live field names; preserve member link |
| Members | name,phone,joinDate,plan/planAmount,status,paidAmount,dueAmount,currentBillingMonth,`planByMonth`,`manualCarryByMonth`,uid | name/email/phone/join_date/monthly_plan/active | Add explicit month-plan and manual-carry storage; expose live-shaped data |
| Payments | uid/name/phone,billingMonth,planAmount,paidAmount/amount,openingCarry,availableAmount,dueAmount,advanceAmount,status,paymentMethod | member_id,amount,payment_date,payment_method,status,reference,notes | Add billing-month/live snapshot fields and CASH/ACCOUNT_TRANSFER mapping; CRUD compatibility |
| Expenses | title,amount,category,paymentMethod,billUrl,billFileId,imageProvider,createdByName | title,amount,category,expense_date,local bill path | Add payment method/creator display metadata; replace cloud upload with local bill endpoint |
| Meals | slot/date/menu | slot/meal_date/menu | Live-shape adapter + update/delete support |
| Meal skips | member uid/date/slot/status/cutoff/realtime | member_id/meal_date/slot/status/cutoff | Live-shape adapter; preserve cutoff and kitchen counts; notification creation |
| Inventory | name,qty,unit,min | name,quantity,unit,minimum_quantity | Live-shape adapter; CRUD/adjust mapping |
| Monthly plans | `planByMonth.YYYY-MM`, plan first for future month | only current `members.monthly_plan` + ledger | Add `member_month_plans` table/API |
| Carry forward | auto prior closing + `manualCarryByMonth.YYYY-MM` | ledger adjustments only | Add explicit `member_month_carry` table/API and calculation |
| Month closing | expense sharing by plan weight × active days; member snapshot; due/advance carry | current close snapshots finance but different algorithm | Replace closing calculation with live semantics; retain immutable snapshot |
| Skip credit | live app closing is expense-share/carry based; skip affects kitchen/meal flow | backend currently subtracts automatic skip credit from plan | Do not double-count closed ledger skip credit; align final calculation with live behavior |
| Reports | month navigation, income/expense/balance/outstanding, CSV | finance summary + data endpoints | Keep client reports; expose required live-shaped data |
| Notifications | in-app live bell from payments/expenses; meal skip notice; Firebase push optional | notifications table + queue | Use API notifications; browser polling/SSE later; no Firebase dependency |
| WhatsApp | `wa.me` prefilled member reminder | queue endpoint exists | Preserve `wa.me` workflow; Meta provider remains optional |
| Bill photos | Cloudinary upload; legacy Uploadcare viewing | local bill storage | Move all new uploads to server; import legacy URLs/files during data migration |
| Backup | browser Firestore backup/restore | PostgreSQL/system backups already exist | Replace with server export/download; no client-side DB restore in production |
| Push | FCM token registration | no production push provider | Keep optional; do not block migration/cutover |
| Gas order | client external action | no backend needed | Preserve client action |

## Confirmed server defects to repair before production

1. `calculate_member_month()` adds stored ledger `skip_credit` to freshly recalculated automatic skip credit. After a month is closed this can double-count skip credit.
2. Current backend has only a single member `monthly_plan`, while generated live app requires month-specific plans.
3. Current monthly closing algorithm differs from the generated live app's plan-weight × active-days expense distribution and due/advance carry semantics.
4. Current payments do not persist the generated live app's billing-month/carry/advance snapshot fields.
5. Current expenses do not persist payment method or creator display name.
6. Existing staging frontend is an old Firebase-converted snapshot and is not the authoritative live UI.

## Build strategy

1. Freeze `migration/generated-live/app.html` as UI source of truth.
2. Add PostgreSQL migration `010_live_parity`.
3. Add FastAPI `live_compat.py` router for live-shaped data/actions.
4. Add browser `techmanz-adapter.js` implementing the subset of Firebase APIs used by the generated app over same-origin `/api/`.
5. Build transformed `migration/server-build/app.html` from generated-live without Firebase/Cloudinary/Uploadcare runtime dependencies.
6. CI checks: no Firebase imports/config; no Cloudinary upload endpoint; JavaScript syntax; required feature markers preserved.
7. Deploy one consolidated package to staging with backup/migrate/rebuild/verify.
8. Import production data only after UI/API parity passes.
9. Cut `a2messhub.app` to secure outbound tunnel -> TECH MANZ server.
