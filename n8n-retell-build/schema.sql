create table if not exists outbound_suppression (
  phone_number text primary key,
  reason text not null,
  source text not null,
  raw_event_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists outbound_campaign_logs (
  id bigint generated always as identity primary key,
  business_id text not null,
  campaign_type text not null,
  phone text not null,
  source_id text,
  channel text not null check (channel in ('sms', 'voice')),
  outcome text not null,
  vendor_message_id text,
  created_at timestamptz not null default now()
);

create table if not exists outbound_workflow_errors (
  id bigint generated always as identity primary key,
  workflow_name text,
  node_name text,
  error_message text,
  execution_id text,
  created_at timestamptz not null default now()
);

create index if not exists outbound_campaign_phone_created_idx
  on outbound_campaign_logs (phone, created_at desc);
