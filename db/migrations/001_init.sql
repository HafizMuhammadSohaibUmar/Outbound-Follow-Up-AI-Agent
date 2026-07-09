create extension if not exists pgcrypto;

create table if not exists campaign_contacts (
    id              uuid primary key default gen_random_uuid(),
    business_id     text not null,
    phone           text not null,
    name            text not null,
    campaign_type   text not null,
    status          text not null default 'pending',
    attempts        integer not null default 0,
    last_attempt_at timestamptz,
    outcome         text,
    custom_data     jsonb not null default '{}'::jsonb,
    created_at      timestamptz not null default now(),
    unique (business_id, phone, campaign_type)
);

create index if not exists idx_campaign_contacts_business_type
    on campaign_contacts (business_id, campaign_type, status);

create table if not exists campaign_logs (
    id            uuid primary key default gen_random_uuid(),
    business_id   text not null,
    campaign_type text not null,
    contact_phone text not null,
    action_type   text not null,
    message_sent  text not null default '',
    outcome       text not null,
    call_sid      text,
    created_at    timestamptz not null default now()
);

create index if not exists idx_campaign_logs_business_type_created
    on campaign_logs (business_id, campaign_type, created_at desc);

create table if not exists campaign_state (
    business_id   text not null,
    campaign_type text not null,
    paused        boolean not null default false,
    updated_at    timestamptz not null default now(),
    primary key (business_id, campaign_type)
);

create table if not exists suppression_list (
    business_id   text not null,
    phone_number  text not null,
    reason        text not null,
    source        text,
    created_at    timestamptz not null default now(),
    primary key (business_id, phone_number)
);

alter table suppression_list add column if not exists source text;
