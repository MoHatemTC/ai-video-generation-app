-- Migration 001: Initial Schema Setup
-- Blueprint mapped directly from PRD Section 10.3 (Core Data Entities)

-- STREAMING_CHUNK: Creating the users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- STREAMING_CHUNK: Creating the videos table to track 8-stage lifecycle
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    
    -- JSON metadata columns mapped to the 8 Pipeline Stages
    script_data JSONB,       -- Stage 1: Transcript (CrewAI)
    scene_data JSONB,        -- Stage 2: Planner (CrewAI)
    audio_metadata JSONB,    -- Stage 3: Audio TTS
    timestamp_data JSONB,    -- Stage 4: Alignment (WhisperX SegmentTimestamps)
    asset_data JSONB,        -- Stage 5: Assets
    composition_data JSONB,  -- Stage 6: Composition Map
    animation_data JSONB,    -- Stage 7: Animation Sync Data
    
    -- Stage 8: Render Output & Error Tracking
    video_url TEXT,
    error_message TEXT,
    
    -- Timestamps and Relations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL
);