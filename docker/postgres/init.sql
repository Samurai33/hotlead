-- HotLead -- PostgreSQL init
-- Runs once on first container creation

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

SET timezone = 'America/Sao_Paulo';
