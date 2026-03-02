-- Fixed schema: create enum types first, then tables in dependency order.
-- Run this in a fresh transaction (or after ROLLBACK if the previous run failed).

BEGIN;

-- 1. Create enum types (required before tables that use them)
DO $$ BEGIN
    CREATE TYPE public.userrole AS ENUM ('admin', 'interviewer', 'candidate');
EXCEPTION
    WHEN duplicate_object THEN NULL;  -- already exists
END $$;

DO $$ BEGIN
    CREATE TYPE public.eventtype AS ENUM (
        'tab_switch', 'paste_event', 'copy_event', 'devtools_detection',
        'idle_time', 'burst_typing', 'instant_large_input', 'webcam_anomaly'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. Tables that do not depend on other app tables (users first)
CREATE TABLE IF NOT EXISTS public.users
(
    id uuid NOT NULL,
    email character varying(255) COLLATE pg_catalog."default" NOT NULL,
    hashed_password character varying(255) COLLATE pg_catalog."default" NOT NULL,
    full_name character varying(255) COLLATE pg_catalog."default",
    role public.userrole NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.candidate_profiles
(
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    job_role character varying(255) COLLATE pg_catalog."default" NOT NULL,
    tech_stack jsonb,
    source character varying(64) COLLATE pg_catalog."default" NOT NULL,
    resume_text text COLLATE pg_catalog."default",
    resume_url character varying(512) COLLATE pg_catalog."default",
    interview_scheduled_at timestamp with time zone,
    status character varying(32) COLLATE pg_catalog."default" NOT NULL,
    invited_at timestamp with time zone,
    photo_url character varying(512) COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    ats_score double precision,
    links jsonb,
    projects jsonb,
    certificates jsonb,
    experience jsonb,
    CONSTRAINT candidate_profiles_pkey PRIMARY KEY (id),
    CONSTRAINT candidate_profiles_user_id_key UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS public.interview_sessions
(
    id uuid NOT NULL,
    session_token character varying(64) COLLATE pg_catalog."default" NOT NULL,
    candidate_id uuid,
    interviewer_id uuid,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    metadata jsonb,
    status character varying(32) COLLATE pg_catalog."default" NOT NULL,
    interview_summary text COLLATE pg_catalog."default",
    video_url character varying(512) COLLATE pg_catalog."default",
    agent_report jsonb,
    face_lip_status character varying(32) COLLATE pg_catalog."default",
    CONSTRAINT interview_sessions_pkey PRIMARY KEY (id)
);

-- 3. Tables that depend on interview_sessions
CREATE TABLE IF NOT EXISTS public.answer_analyses
(
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    question_id character varying(64) COLLATE pg_catalog."default",
    answer_text text COLLATE pg_catalog."default",
    words_per_second double precision,
    ai_probability double precision,
    features jsonb,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT answer_analyses_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.integrity_scores
(
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    score double precision NOT NULL,
    risk_level character varying(16) COLLATE pg_catalog."default" NOT NULL,
    penalties jsonb,
    computed_at timestamp with time zone NOT NULL,
    CONSTRAINT integrity_scores_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.interview_exchanges
(
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    question_index integer NOT NULL,
    question_text text COLLATE pg_catalog."default" NOT NULL,
    answer_text text COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp with time zone NOT NULL,
    answered_quickly boolean DEFAULT false,
    CONSTRAINT interview_exchanges_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.session_photos
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    photo_url character varying(512) COLLATE pg_catalog."default" NOT NULL,
    captured_at timestamp with time zone DEFAULT now(),
    face_detected boolean DEFAULT true,
    CONSTRAINT session_photos_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.suspicious_events
(
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    event_type public.eventtype NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    payload jsonb,
    severity character varying(16) COLLATE pg_catalog."default",
    CONSTRAINT suspicious_events_pkey PRIMARY KEY (id)
);

-- 4. Foreign keys
ALTER TABLE IF EXISTS public.candidate_profiles
    DROP CONSTRAINT IF EXISTS candidate_profiles_user_id_fkey;
ALTER TABLE public.candidate_profiles
    ADD CONSTRAINT candidate_profiles_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES public.users (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_candidate_profiles_user_id ON public.candidate_profiles(user_id);

ALTER TABLE IF EXISTS public.interview_sessions
    DROP CONSTRAINT IF EXISTS interview_sessions_candidate_id_fkey;
ALTER TABLE public.interview_sessions
    ADD CONSTRAINT interview_sessions_candidate_id_fkey FOREIGN KEY (candidate_id)
    REFERENCES public.users (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE IF EXISTS public.interview_sessions
    DROP CONSTRAINT IF EXISTS interview_sessions_interviewer_id_fkey;
ALTER TABLE public.interview_sessions
    ADD CONSTRAINT interview_sessions_interviewer_id_fkey FOREIGN KEY (interviewer_id)
    REFERENCES public.users (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE IF EXISTS public.answer_analyses
    DROP CONSTRAINT IF EXISTS answer_analyses_session_id_fkey;
ALTER TABLE public.answer_analyses
    ADD CONSTRAINT answer_analyses_session_id_fkey FOREIGN KEY (session_id)
    REFERENCES public.interview_sessions (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE IF EXISTS public.integrity_scores
    DROP CONSTRAINT IF EXISTS integrity_scores_session_id_fkey;
ALTER TABLE public.integrity_scores
    ADD CONSTRAINT integrity_scores_session_id_fkey FOREIGN KEY (session_id)
    REFERENCES public.interview_sessions (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE IF EXISTS public.interview_exchanges
    DROP CONSTRAINT IF EXISTS interview_exchanges_session_id_fkey;
ALTER TABLE public.interview_exchanges
    ADD CONSTRAINT interview_exchanges_session_id_fkey FOREIGN KEY (session_id)
    REFERENCES public.interview_sessions (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE IF EXISTS public.session_photos
    DROP CONSTRAINT IF EXISTS session_photos_session_id_fkey;
ALTER TABLE public.session_photos
    ADD CONSTRAINT session_photos_session_id_fkey FOREIGN KEY (session_id)
    REFERENCES public.interview_sessions (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE IF EXISTS public.suspicious_events
    DROP CONSTRAINT IF EXISTS suspicious_events_session_id_fkey;
ALTER TABLE public.suspicious_events
    ADD CONSTRAINT suspicious_events_session_id_fkey FOREIGN KEY (session_id)
    REFERENCES public.interview_sessions (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE;

COMMIT;
