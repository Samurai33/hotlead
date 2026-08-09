// Shared between the client-side proxy fetcher (lib/api.ts) and the
// server-side direct fetcher (lib/server-api.ts) so both speak the same
// backend response shapes without importing each other across the
// client/server boundary.

export type JobMode = "followers" | "following" | "commenters";
export type JobStatus = "pending" | "running" | "paused" | "done" | "error";

export interface Job {
  id: string;
  profile_username: string;
  mode: JobMode;
  status: JobStatus;
  total_count: number;
  scraped_count: number;
  emails_found: number;
  phones_found: number;
  target_post_url: string | null;
  celery_task_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobSummary {
  id: string;
  profile_username: string;
  mode: JobMode;
  status: JobStatus;
  total_count: number;
  scraped_count: number;
  emails_found: number;
  phones_found: number;
  created_at: string;
}

export interface Prospect {
  id: string;
  username: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  biography: string | null;
  followers: number;
  following: number;
  is_business: boolean;
  is_verified: boolean;
  created_at: string;
}

export type AccountStatus = "active" | "cooldown" | "session_expired" | "banned";

export interface Account {
  id: string;
  username: string;
  proxy_url: string;
  status: AccountStatus;
  requests_today: number;
  last_used_at: string | null;
  cooldown_until: string | null;
  created_at: string;
}
