-- Supabase Database Schema
-- Run these SQL commands in your Supabase SQL Editor to create the required tables

-- ============================================================================
-- Users Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);

-- ============================================================================
-- Support Cases Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_cases (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id) ON DELETE CASCADE,
    original_case TEXT NOT NULL,
    translated_case TEXT NOT NULL,
    task_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'pending_reminder')),
    support_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_support_cases_user_id ON support_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_support_cases_task_number ON support_cases(task_number);
CREATE INDEX IF NOT EXISTS idx_support_cases_status ON support_cases(status);

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_cases ENABLE ROW LEVEL SECURITY;

-- Policy: Allow insert for registration (anonymous access)
CREATE POLICY "Allow insert for registration" ON users
    FOR INSERT
    WITH CHECK (true);

-- Policy: Allow select for authentication
CREATE POLICY "Allow select for authentication" ON users
    FOR SELECT
    USING (true);

-- Policy: Allow all operations on support_cases for authenticated service role
CREATE POLICY "Allow all for support_cases" ON support_cases
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- Updated At Trigger
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for support_cases table
CREATE TRIGGER update_support_cases_updated_at
    BEFORE UPDATE ON support_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
