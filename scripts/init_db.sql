-- Create database if it doesn't exist
SELECT 'CREATE DATABASE integration_service'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'integration_service')\gexec

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create enum types
CREATE TYPE sync_status_enum AS ENUM ('pending', 'synced', 'failed', 'completed');
CREATE TYPE provider_type_enum AS ENUM ('servicetitan', 'housecallpro', 'mock');

-- Create companies table with provider configuration
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    provider_type provider_type_enum DEFAULT 'mock',
    provider_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create technicians table
CREATE TABLE IF NOT EXISTS technicians (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create jobs table with all required fields
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by_company_id UUID NOT NULL REFERENCES companies(id),
    created_by_technician_id UUID NOT NULL REFERENCES technicians(id),
    summary TEXT NOT NULL,
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    homeowner_name VARCHAR(255) NOT NULL,
    homeowner_phone VARCHAR(20),
    homeowner_email VARCHAR(255),
    revenue NUMERIC(10,2),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create job_routings table with sync tracking
CREATE TABLE IF NOT EXISTS job_routings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    company_id_received UUID NOT NULL REFERENCES companies(id),
    external_id VARCHAR(255) UNIQUE, -- ID in external system (ServiceTitan)
    sync_status sync_status_enum DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    total_sync_attempts INTEGER DEFAULT 0,
    last_sync_attempt TIMESTAMP WITH TIME ZONE,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_companies_provider_type ON companies(provider_type) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_job_routings_sync_status ON job_routings(sync_status);
CREATE INDEX IF NOT EXISTS idx_job_routings_company_status ON job_routings(company_id_received, sync_status);
CREATE INDEX IF NOT EXISTS idx_job_routings_last_synced ON job_routings(last_synced_at) WHERE sync_status = 'synced';
CREATE INDEX IF NOT EXISTS idx_job_routings_retry ON job_routings(sync_status, retry_count, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_company_tech ON jobs(created_by_company_id, created_by_technician_id);
CREATE INDEX IF NOT EXISTS idx_technicians_company ON technicians(company_id);

-- Add triggers to update updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_technicians_updated_at BEFORE UPDATE ON technicians
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_routings_updated_at BEFORE UPDATE ON job_routings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();