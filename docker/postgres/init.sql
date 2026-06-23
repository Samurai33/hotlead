-- HotLead — PostgreSQL initialization
-- Runs once when the container is first created

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- trigram search for usernames

-- Set timezone
SET timezone = 'America/Sao_Paulo';
