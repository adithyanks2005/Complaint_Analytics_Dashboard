-- Supabase migration placeholder
-- Creates the complaints table matching the backend schema.
-- This file allows Supabase preview to run without errors.

CREATE TABLE IF NOT EXISTS complaints (
    id TEXT PRIMARY KEY,
    created_date TEXT NOT NULL,
    closed_date TEXT,
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
