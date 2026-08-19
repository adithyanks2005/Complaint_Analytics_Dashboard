-- Production schema for Complaint Analytics Dashboard.
-- Supabase is the authoritative production datastore. The application must not
-- silently fall back to SQLite when this database is configured.

CREATE TABLE IF NOT EXISTS complaints (
    id TEXT PRIMARY KEY,
    created_date DATE NOT NULL,
    closed_date DATE,
    state TEXT,
    district TEXT,
    municipality TEXT,
    village TEXT,
    area TEXT NOT NULL,
    pincode TEXT,
    category TEXT NOT NULL,
    priority TEXT,
    status TEXT NOT NULL DEFAULT 'Pending',
    description TEXT NOT NULL,
    user_contact TEXT,
    image_path TEXT
);

-- Repair legacy rows before enforcing the state invariants.
UPDATE complaints
SET closed_date = NULL
WHERE status IS NULL OR status <> 'Closed';

UPDATE complaints
SET status = 'Pending', closed_date = NULL
WHERE status = 'Closed' AND closed_date IS NULL;

UPDATE complaints
SET status = 'Pending'
WHERE status NOT IN ('Pending', 'In Progress', 'Closed');

UPDATE complaints
SET priority = NULL
WHERE priority NOT IN ('Low', 'Medium', 'High');

ALTER TABLE complaints
    ALTER COLUMN status SET DEFAULT 'Pending';

ALTER TABLE complaints
    DROP CONSTRAINT IF EXISTS complaints_status_check;
ALTER TABLE complaints
    DROP CONSTRAINT IF EXISTS complaints_priority_check;
ALTER TABLE complaints
    DROP CONSTRAINT IF EXISTS complaints_state_dates_check;
ALTER TABLE complaints
    DROP CONSTRAINT IF EXISTS complaints_date_order_check;

ALTER TABLE complaints
    ADD CONSTRAINT complaints_status_check
    CHECK (status IN ('Pending', 'In Progress', 'Closed'));

ALTER TABLE complaints
    ADD CONSTRAINT complaints_priority_check
    CHECK (priority IS NULL OR priority IN ('Low', 'Medium', 'High'));

ALTER TABLE complaints
    ADD CONSTRAINT complaints_state_dates_check
    CHECK (
        (status = 'Closed' AND closed_date IS NOT NULL)
        OR (status <> 'Closed' AND closed_date IS NULL)
    );

ALTER TABLE complaints
    ADD CONSTRAINT complaints_date_order_check
    CHECK (closed_date IS NULL OR closed_date >= created_date);

-- Database-owned, atomic public complaint ID generation.
CREATE SEQUENCE IF NOT EXISTS complaint_id_seq;

SELECT setval(
    'complaint_id_seq',
    GREATEST(
        COALESCE((
            SELECT MAX((regexp_match(id, '^CMP-([0-9]+)$'))[1]::BIGINT)
            FROM complaints
            WHERE id ~ '^CMP-[0-9]+$'
        ), 0),
        0
    ),
    true
);

CREATE OR REPLACE FUNCTION assign_complaint_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.id IS NULL OR btrim(NEW.id) = '' THEN
        NEW.id := 'CMP-' || lpad(nextval('complaint_id_seq')::text, 3, '0');
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS complaints_assign_id ON complaints;
CREATE TRIGGER complaints_assign_id
BEFORE INSERT ON complaints
FOR EACH ROW
EXECUTE FUNCTION assign_complaint_id();

-- Keep service-role access available while preventing accidental anonymous
-- access if the table is exposed through PostgREST.
ALTER TABLE complaints ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS complaints_service_role_all ON complaints;
CREATE POLICY complaints_service_role_all
ON complaints
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_complaints_created_date ON complaints(created_date);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category);
CREATE INDEX IF NOT EXISTS idx_complaints_area ON complaints(area);
