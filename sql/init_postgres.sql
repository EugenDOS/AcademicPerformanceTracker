-- PostgreSQL setup for Academic Performance Tracker.
-- Run this script as a PostgreSQL superuser, for example:
-- psql -U postgres -f sql/init_postgres.sql
--
-- The script creates only the database, user and permissions.
-- Django tables are created by:
-- python manage.py migrate

\set app_db academic_performance_tracker
\set app_user academic_tracker_user
\set app_password 'academic_tracker_password'

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'academic_tracker_user'
    ) THEN
        CREATE ROLE academic_tracker_user
            LOGIN
            PASSWORD 'academic_tracker_password'
            CREATEDB;
    ELSE
        ALTER ROLE academic_tracker_user
            LOGIN
            PASSWORD 'academic_tracker_password'
            CREATEDB;
    END IF;
END
$$;

SELECT 'CREATE DATABASE academic_performance_tracker
        OWNER academic_tracker_user
        ENCODING ''UTF8''
        TEMPLATE template0'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'academic_performance_tracker'
)\gexec

\connect academic_performance_tracker

GRANT ALL PRIVILEGES ON DATABASE academic_performance_tracker TO academic_tracker_user;
GRANT ALL ON SCHEMA public TO academic_tracker_user;
ALTER SCHEMA public OWNER TO academic_tracker_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO academic_tracker_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO academic_tracker_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON FUNCTIONS TO academic_tracker_user;

