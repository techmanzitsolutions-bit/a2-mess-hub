BEGIN;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'system','config',jsonb_build_object(
  'initialized',true,
  'ownerUid',COALESCE((SELECT id::text FROM users WHERE role='admin' AND active=TRUE ORDER BY created_at LIMIT 1),''),
  'ownerEmail',COALESCE((SELECT email FROM users WHERE role='admin' AND active=TRUE ORDER BY created_at LIMIT 1),''),
  'imageProvider','local',
  'mealAlertAdminPhone','',
  'mealAlertAdminEmail','',
  'mealAlertChefPhone','',
  'mealAlertChefEmail',''
)
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'users',u.id::text,
  jsonb_build_object(
    'uid',u.id::text,
    'name',u.name,
    'email',COALESCE(u.email,''),
    'phone',COALESCE(u.phone,''),
    'role',u.role,
    'active',u.active,
    'memberId',COALESCE(m.id::text,''),
    'createdAt',u.created_at,
    'updatedAt',u.updated_at
  )
FROM users u
LEFT JOIN members m ON m.user_id=u.id
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'members',m.id::text,
  jsonb_build_object(
    'uid',COALESCE(m.user_id::text,''),
    'name',m.name,
    'email',COALESCE(m.email,''),
    'phone',COALESCE(m.phone,''),
    'plan','AED ' || trim(to_char(m.monthly_plan,'FM999999990.00')),
    'planAmount',m.monthly_plan,
    'joinDate',m.join_date,
    'active',m.active,
    'createdAt',m.created_at,
    'updatedAt',m.updated_at
  )
FROM members m
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'inventory',i.id::text,
  jsonb_build_object(
    'name',i.name,'qty',i.quantity,'unit',COALESCE(i.unit,''),'min',i.minimum_quantity,
    'active',i.active,'createdAt',i.created_at,'updatedAt',i.updated_at
  )
FROM inventory i
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'meals',m.id::text,
  jsonb_build_object(
    'slot',initcap(m.slot),'date',m.meal_date,'menu',COALESCE(m.menu,''),
    'createdAt',m.created_at,'updatedAt',m.updated_at
  )
FROM meals m
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'expenses',e.id::text,
  jsonb_build_object(
    'title',e.title,'amount',e.amount,'category',COALESCE(e.category,'General'),
    'billUrl','','billFileId','','imageProvider','local','paymentMethod','CASH',
    'createdBy',COALESCE(e.created_by::text,''),'createdAt',e.created_at,'updatedAt',e.updated_at
  )
FROM expenses e
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'payments',p.id::text,
  jsonb_build_object(
    'uid',COALESCE(m.user_id::text,m.id::text),
    'name',m.name,
    'phone',COALESCE(m.phone,''),
    'billingMonth',to_char(p.payment_date,'YYYY-MM'),
    'planAmount',m.monthly_plan,
    'paidAmount',p.amount,
    'amount',p.amount,
    'status',upper(p.status),
    'paymentMethod',CASE WHEN lower(p.payment_method) IN ('bank','card') THEN 'ACCOUNT_TRANSFER' ELSE 'CASH' END,
    'reference',COALESCE(p.reference,''),'notes',COALESCE(p.notes,''),
    'createdAt',p.created_at,'updatedAt',p.updated_at
  )
FROM payments p
JOIN members m ON m.id=p.member_id
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO live_documents(collection,doc_id,data)
SELECT 'mealSkips',s.id::text,
  jsonb_build_object(
    'uid',COALESCE(m.user_id::text,m.id::text),
    'memberId',m.id::text,
    'memberName',m.name,
    'date',s.meal_date,
    'meal',initcap(s.slot),
    'status',CASE WHEN lower(s.status)='skipped' THEN 'SKIPPED' ELSE upper(s.status) END,
    'cutoffAt',s.cutoff_at,
    'createdAt',s.created_at,
    'updatedAt',s.updated_at
  )
FROM meal_skips s
JOIN members m ON m.id=s.member_id
ON CONFLICT(collection,doc_id) DO NOTHING;

INSERT INTO migration_log(migration_name,status)
SELECT '011_seed_compat_from_staging','completed'
WHERE NOT EXISTS(SELECT 1 FROM migration_log WHERE migration_name='011_seed_compat_from_staging');

COMMIT;
