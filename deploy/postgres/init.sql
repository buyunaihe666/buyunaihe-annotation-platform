-- Auto-create labelhub_agent database for the Agent service
SELECT 'CREATE DATABASE labelhub_agent'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'labelhub_agent')\gexec
