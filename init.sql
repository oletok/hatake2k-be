-- Initialize database user and permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'hatake_user') THEN
        CREATE USER hatake_user WITH PASSWORD 'hatake_password';
    END IF;
END
$$;
ALTER USER hatake_user CREATEDB;
ALTER USER hatake_user WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE hatake TO hatake_user;