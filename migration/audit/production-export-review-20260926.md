# Production export review — 2026-09-26

Reviewed source export:
- format: A2-MESS-HUB-PRODUCTION-EXPORT v1
- project: a2-mess-hub
- exportedAt: 2026-09-26T07:21:14.195Z
- SHA-256: 618436a6d650082c91717ca2c61fcbdbbbcb2deb9508ae79d5606479f572ca28

Document counts:
- users: 12
- members: 11
- inventory: 0
- meals: 2
- mealSkips: 5
- expenses: 58
- payments: 29
- monthlyClosings: 1
- settings: 0
- notifications: 0
- system: 1

Financial cross-checks:
- payment records total: AED 2,890.13
- expense records total: AED 1,570.18
- payments by billing month: 2026-09 = 28 records / AED 2,790.13; 2026-10 = 1 record / AED 100.00
- expenses: 58 records in 2026-09 / AED 1,570.18

External storage:
- 47 expense records have Cloudinary bill URLs
- 11 expense records have no bill URL
- the production importer attempts to copy all 47 Cloudinary bill images into TECH MANZ local storage before cutover

Identity migration:
- 12 production profiles: 1 admin, 1 chef, 10 members
- production Firebase passwords are not present in the client Firestore export
- existing matching TECH MANZ logins are preserved by email
- missing local logins receive migration-only temporary passwords and are login-tested before completion
- Firebase UIDs embedded in application documents are mapped to the corresponding TECH MANZ local user UUIDs

Cutover gate:
- exact reviewed export timestamp/counts/financial totals must match
- post-import collection counts and totals must match
- external bill URL count must be zero before final cutover
- production Firebase is not modified by the importer
