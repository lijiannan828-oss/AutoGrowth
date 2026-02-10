-- Grant permissions to IAM database user
-- Connect to auto_growth database first
\c auto_growth

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE auto_growth TO "sa-dev@fleet-blend-469520-n7.iam";

-- Grant all privileges on schema
GRANT ALL PRIVILEGES ON SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam";

-- Grant all privileges on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam";

-- Grant all privileges on all sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "sa-dev@fleet-blend-469520-n7.iam";

-- Grant privileges on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "sa-dev@fleet-blend-469520-n7.iam";

-- Grant privileges on future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "sa-dev@fleet-blend-469520-n7.iam";

