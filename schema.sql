-- ════════════════════════════════════════════
--  APEX AGENT — Supabase Schema
--  Paste into: Supabase → SQL Editor → Run
-- ════════════════════════════════════════════

create table if not exists jobs (
  id              uuid primary key default gen_random_uuid(),
  title           text not null,
  company         text not null,
  location        text,
  source          text,                         -- linkedin | indeed | glassdoor | zip_recruiter
  url             text unique,
  description     text,
  salary_min      integer,
  salary_max      integer,
  score           integer,                      -- 0–100
  score_reasoning text,
  status          text default 'new',           -- new | reviewed | applied | interviewing | offer | rejected
  found_at        timestamptz default now(),
  updated_at      timestamptz default now()
);

create table if not exists drafts (
  id              uuid primary key default gen_random_uuid(),
  job_id          uuid references jobs(id) on delete cascade,
  cover_letter    text,
  email_subject   text,
  email_body      text,
  linkedin_note   text,
  approved        boolean default false,
  edited          boolean default false,
  sent_at         timestamptz,
  created_at      timestamptz default now()
);

create table if not exists email_threads (
  id              uuid primary key default gen_random_uuid(),
  job_id          uuid references jobs(id) on delete set null,
  gmail_thread_id text unique,
  sender_name     text,
  sender_email    text,
  subject         text,
  last_message    text,
  intent          text,                         -- interview_request | rejection | info_request | offer | other
  draft_reply     text,
  reply_approved  boolean default false,
  replied_at      timestamptz,
  received_at     timestamptz default now()
);

-- Auto-update updated_at on jobs
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger jobs_updated_at
  before update on jobs
  for each row execute function update_updated_at();

-- Indexes
create index if not exists jobs_status_idx on jobs(status);
create index if not exists jobs_score_idx on jobs(score desc);
create index if not exists jobs_source_idx on jobs(source);
