-- PPL Checkride User Progress Schema
-- Database: Supabase (PostgreSQL)

-- Table: user_progress
-- Stores individual question progress for each user
CREATE TABLE user_progress (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    license_key_hash TEXT NOT NULL,
    question_id TEXT NOT NULL,
    rating TEXT CHECK (rating IN ('mastered', 'review', 'practice')),
    attempts INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    last_attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one record per user per question
    UNIQUE(license_key_hash, question_id)
);

-- Table: mock_checkride_results
-- Stores mock checkride attempts and scores
CREATE TABLE mock_checkride_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    license_key_hash TEXT NOT NULL,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    passed BOOLEAN NOT NULL,
    time_spent_seconds INTEGER,
    questions_attempted JSONB, -- Array of question IDs attempted
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: user_sessions
-- Tracks active sessions and last sync time
CREATE TABLE user_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    license_key_hash TEXT NOT NULL UNIQUE,
    last_sync_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_questions_attempted INTEGER DEFAULT 0,
    total_study_time_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_user_progress_license ON user_progress(license_key_hash);
CREATE INDEX idx_user_progress_question ON user_progress(question_id);
CREATE INDEX idx_user_progress_rating ON user_progress(rating);
CREATE INDEX idx_mock_results_license ON mock_checkride_results(license_key_hash);
CREATE INDEX idx_mock_results_completed ON mock_checkride_results(completed_at);
CREATE INDEX idx_user_sessions_license ON user_sessions(license_key_hash);

-- Function: Update timestamp on row update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at
CREATE TRIGGER update_user_progress_updated_at
    BEFORE UPDATE ON user_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE mock_checkride_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own data
-- Note: In production, you'd validate license_key_hash matches authenticated user
CREATE POLICY "Users can view own progress"
    ON user_progress FOR SELECT
    USING (true); -- Allow all reads (license key validation done in app)

CREATE POLICY "Users can insert own progress"
    ON user_progress FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can update own progress"
    ON user_progress FOR UPDATE
    USING (true);

CREATE POLICY "Users can view own mock results"
    ON mock_checkride_results FOR SELECT
    USING (true);

CREATE POLICY "Users can insert own mock results"
    ON mock_checkride_results FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can view own session"
    ON user_sessions FOR SELECT
    USING (true);

CREATE POLICY "Users can insert own session"
    ON user_sessions FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can update own session"
    ON user_sessions FOR UPDATE
    USING (true);

-- Example queries for common operations:

-- Get user's progress summary
-- SELECT 
--     COUNT(*) FILTER (WHERE rating = 'mastered') as mastered_count,
--     COUNT(*) FILTER (WHERE rating = 'review') as review_count,
--     COUNT(*) FILTER (WHERE rating = 'practice') as practice_count,
--     COUNT(*) as total_attempted
-- FROM user_progress
-- WHERE license_key_hash = 'hash_here';

-- Get user's recent mock checkride attempts
-- SELECT * FROM mock_checkride_results
-- WHERE license_key_hash = 'hash_here'
-- ORDER BY completed_at DESC
-- LIMIT 10;

-- Upsert user progress (update if exists, insert if not)
-- INSERT INTO user_progress (license_key_hash, question_id, rating, attempts, correct_count)
-- VALUES ('hash', 'Q1', 'mastered', 1, 1)
-- ON CONFLICT (license_key_hash, question_id)
-- DO UPDATE SET
--     rating = EXCLUDED.rating,
--     attempts = user_progress.attempts + 1,
--     correct_count = user_progress.correct_count + EXCLUDED.correct_count,
--     last_attempted_at = NOW();
