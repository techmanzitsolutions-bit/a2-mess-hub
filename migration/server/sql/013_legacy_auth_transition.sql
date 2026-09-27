BEGIN;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS legacy_auth_migrated_at timestamptz;

UPDATE users
SET legacy_auth_migrated_at=COALESCE(legacy_auth_migrated_at,NOW())
WHERE active=TRUE
  AND lower(email)=lower('a.hakkim7468@gmail.com');

COMMIT;
