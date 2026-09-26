BEGIN;

ALTER TABLE members
  ADD COLUMN IF NOT EXISTS legacy_live_id text,
  ADD COLUMN IF NOT EXISTS current_billing_month text,
  ADD COLUMN IF NOT EXISTS status text,
  ADD COLUMN IF NOT EXISTS paid_amount numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS due_amount numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS advance_amount numeric(12,2) NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS members_legacy_live_id_uq
  ON members(legacy_live_id) WHERE legacy_live_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS member_month_plans (
  id uuid PRIMARY KEY,
  member_id uuid NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  billing_month date NOT NULL,
  plan_amount numeric(12,2) NOT NULL CHECK (plan_amount >= 0),
  created_by uuid NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(member_id,billing_month)
);

CREATE TABLE IF NOT EXISTS member_month_carry (
  id uuid PRIMARY KEY,
  member_id uuid NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  billing_month date NOT NULL,
  amount numeric(12,2) NOT NULL DEFAULT 0,
  source text NOT NULL DEFAULT 'manual',
  created_by uuid NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(member_id,billing_month)
);

ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS billing_month date,
  ADD COLUMN IF NOT EXISTS plan_amount numeric(12,2),
  ADD COLUMN IF NOT EXISTS opening_carry numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS available_amount numeric(12,2),
  ADD COLUMN IF NOT EXISTS due_amount numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS advance_amount numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS display_name text,
  ADD COLUMN IF NOT EXISTS display_phone text,
  ADD COLUMN IF NOT EXISTS legacy_live_id text;

UPDATE payments
SET billing_month = date_trunc('month', payment_date)::date
WHERE billing_month IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS payments_legacy_live_id_uq
  ON payments(legacy_live_id) WHERE legacy_live_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS payments_member_month_idx
  ON payments(member_id,billing_month);

ALTER TABLE expenses
  ADD COLUMN IF NOT EXISTS payment_method text NOT NULL DEFAULT 'CASH',
  ADD COLUMN IF NOT EXISTS created_by_name text,
  ADD COLUMN IF NOT EXISTS image_provider text,
  ADD COLUMN IF NOT EXISTS legacy_bill_url text,
  ADD COLUMN IF NOT EXISTS legacy_bill_file_id text,
  ADD COLUMN IF NOT EXISTS legacy_live_id text;

CREATE UNIQUE INDEX IF NOT EXISTS expenses_legacy_live_id_uq
  ON expenses(legacy_live_id) WHERE legacy_live_id IS NOT NULL;

ALTER TABLE meals
  ADD COLUMN IF NOT EXISTS legacy_live_id text;
CREATE UNIQUE INDEX IF NOT EXISTS meals_legacy_live_id_uq
  ON meals(legacy_live_id) WHERE legacy_live_id IS NOT NULL;

ALTER TABLE inventory
  ADD COLUMN IF NOT EXISTS legacy_live_id text;
CREATE UNIQUE INDEX IF NOT EXISTS inventory_legacy_live_id_uq
  ON inventory(legacy_live_id) WHERE legacy_live_id IS NOT NULL;

ALTER TABLE meal_skips
  ADD COLUMN IF NOT EXISTS legacy_live_id text;
CREATE UNIQUE INDEX IF NOT EXISTS meal_skips_legacy_live_id_uq
  ON meal_skips(legacy_live_id) WHERE legacy_live_id IS NOT NULL;

ALTER TABLE monthly_closings
  ADD COLUMN IF NOT EXISTS member_snapshot jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS total_due_carry numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_advance_carry numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_weight numeric(18,6) NOT NULL DEFAULT 0;

INSERT INTO migration_log(migration_name,status,executed_at)
VALUES('010_live_parity','applied',now())
ON CONFLICT (migration_name) DO NOTHING;

COMMIT;
