create extension if not exists "pgcrypto";
create extension if not exists "pg_trgm";

create table organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  org_type text not null check (org_type in ('regulator','bank','mfs','nbfi')),
  bank_code text unique,
  plan text not null default 'standard',
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  org_id uuid not null references organizations(id),
  full_name text not null,
  role text not null default 'analyst' check (role in ('superadmin','admin','manager','analyst','viewer')),
  persona text not null default 'bfiu_analyst' check (persona in ('bfiu_analyst','bank_camlco','bfiu_director')),
  designation text,
  created_at timestamptz not null default now()
);

create table entities (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in ('account','phone','wallet','nid','device','ip','url','person','business')),
  canonical_value text not null,
  display_value text not null,
  display_name text,
  risk_score integer check (risk_score between 0 and 100),
  severity text check (severity in ('critical','high','medium','low')),
  confidence numeric(3,2) not null default 0.50,
  status text not null default 'active' check (status in ('active','confirmed','investigating','cleared','archived')),
  source text not null default 'system',
  reporting_orgs uuid[] not null default '{}',
  report_count integer not null default 0,
  first_seen timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  total_exposure numeric(18,2) not null default 0,
  tags text[] not null default '{}',
  notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(entity_type, canonical_value)
);

create table connections (
  id uuid primary key default gen_random_uuid(),
  from_entity_id uuid not null references entities(id) on delete cascade,
  to_entity_id uuid not null references entities(id) on delete cascade,
  relation text not null check (relation in ('transacted','same_owner','shared_device','shared_phone','shared_address','beneficiary','co_reported','account_of')),
  weight numeric(5,2) not null default 1.0,
  evidence jsonb not null default '{}'::jsonb,
  first_seen timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  unique(from_entity_id, to_entity_id, relation)
);

create table str_reports (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id),
  report_ref text not null,
  status text not null default 'submitted' check (status in ('draft','submitted','under_review','flagged','confirmed','dismissed')),
  subject_name text,
  subject_account text not null,
  subject_bank text,
  subject_phone text,
  subject_wallet text,
  subject_nid text,
  total_amount numeric(18,2) not null default 0,
  currency text not null default 'BDT',
  transaction_count integer not null default 0,
  primary_channel text,
  channels text[] not null default '{}',
  date_range_start date,
  date_range_end date,
  category text not null check (category in ('fraud','money_laundering','terrorist_financing','tbml','cyber_crime','other')),
  narrative text,
  auto_risk_score integer,
  matched_entity_ids uuid[] not null default '{}',
  cross_bank_hit boolean not null default false,
  submitted_by uuid references auth.users(id),
  reviewed_by uuid references auth.users(id),
  metadata jsonb not null default '{}'::jsonb,
  reported_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table matches (
  id uuid primary key default gen_random_uuid(),
  entity_id uuid references entities(id),
  match_key text not null,
  match_type text not null,
  involved_org_ids uuid[] not null,
  involved_str_ids uuid[] not null,
  match_count integer not null,
  total_exposure numeric(18,2) not null default 0,
  risk_score integer,
  severity text check (severity in ('critical','high','medium','low')),
  status text not null default 'new' check (status in ('new','investigating','confirmed','false_positive')),
  assigned_to uuid references auth.users(id),
  notes jsonb not null default '[]'::jsonb,
  detected_at timestamptz not null default now(),
  unique(match_type, match_key)
);

create table accounts (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id),
  account_number text not null,
  account_name text,
  bank_code text,
  account_type text,
  risk_tier text not null default 'normal',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(org_id, account_number)
);

create table transactions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id),
  run_id uuid,
  posted_at timestamptz not null,
  src_account_id uuid references accounts(id),
  dst_account_id uuid references accounts(id),
  amount numeric(18,2) not null,
  currency text not null default 'BDT',
  channel text,
  tx_type text,
  description text,
  balance_after numeric(18,2),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table detection_runs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id),
  run_type text not null check (run_type in ('upload','scheduled','str_triggered','api')),
  status text not null default 'pending' check (status in ('pending','processing','completed','failed')),
  file_name text,
  file_url text,
  tx_count integer not null default 0,
  accounts_scanned integer not null default 0,
  alerts_generated integer not null default 0,
  results jsonb not null default '{}'::jsonb,
  triggered_by uuid references auth.users(id),
  started_at timestamptz,
  completed_at timestamptz,
  error text,
  created_at timestamptz not null default now()
);

create table alerts (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id),
  source_type text not null check (source_type in ('scan','cross_bank','str_enrichment','manual')),
  source_id uuid,
  entity_id uuid references entities(id),
  title text not null,
  description text,
  alert_type text not null,
  risk_score integer not null check (risk_score between 0 and 100),
  severity text not null check (severity in ('critical','high','medium','low')),
  status text not null default 'open' check (status in ('open','reviewing','escalated','true_positive','false_positive')),
  reasons jsonb not null default '[]'::jsonb,
  assigned_to uuid references auth.users(id),
  case_id uuid,
  resolved_by uuid references auth.users(id),
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table cases (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id),
  case_ref text not null,
  title text not null,
  summary text,
  category text,
  severity text not null check (severity in ('critical','high','medium','low')),
  status text not null default 'open' check (status in ('open','investigating','escalated','pending_action','closed_confirmed','closed_false_positive')),
  assigned_to uuid references auth.users(id),
  linked_alert_ids uuid[] not null default '{}',
  linked_entity_ids uuid[] not null default '{}',
  total_exposure numeric(18,2) not null default 0,
  recovered numeric(18,2) not null default 0,
  timeline jsonb not null default '[]'::jsonb,
  tags text[] not null default '{}',
  due_date date,
  closed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table rules (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id),
  code text not null,
  name text not null,
  description text,
  category text not null,
  is_active boolean not null default true,
  is_system boolean not null default false,
  weight numeric(4,2) not null default 1.0,
  definition jsonb not null default '{}'::jsonb,
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(org_id, code)
);

create table audit_log (
  id bigint generated always as identity primary key,
  org_id uuid references organizations(id),
  user_id uuid references auth.users(id),
  action text not null,
  resource_type text,
  resource_id uuid,
  details jsonb not null default '{}'::jsonb,
  ip inet,
  created_at timestamptz not null default now()
);

create index idx_entities_lookup on entities(entity_type, canonical_value);
create index idx_entities_display_trgm on entities using gin(display_value gin_trgm_ops);
create index idx_connections_from on connections(from_entity_id);
create index idx_connections_to on connections(to_entity_id);
create index idx_str_org on str_reports(org_id);
create index idx_str_account on str_reports(subject_account);
create index idx_matches_score on matches(risk_score desc nulls last);
create index idx_transactions_org_time on transactions(org_id, posted_at desc);
create index idx_alerts_org on alerts(org_id);
create index idx_alerts_created on alerts(created_at desc);
create index idx_cases_org on cases(org_id);
create index idx_audit_org_time on audit_log(org_id, created_at desc);

alter table organizations enable row level security;
alter table profiles enable row level security;
alter table entities enable row level security;
alter table connections enable row level security;
alter table str_reports enable row level security;
alter table matches enable row level security;
alter table accounts enable row level security;
alter table transactions enable row level security;
alter table detection_runs enable row level security;
alter table alerts enable row level security;
alter table cases enable row level security;
alter table rules enable row level security;
alter table audit_log enable row level security;

create or replace function auth_org_id() returns uuid as $$
  select org_id from profiles where id = auth.uid()
$$ language sql security definer stable;

create or replace function is_regulator() returns boolean as $$
  select exists (
    select 1
    from profiles p
    join organizations o on o.id = p.org_id
    where p.id = auth.uid() and o.org_type = 'regulator'
  )
$$ language sql security definer stable;

create policy profiles_own_org on profiles for all using (org_id = auth_org_id() or is_regulator());
create policy organizations_visible on organizations for select using (id = auth_org_id() or is_regulator());
create policy str_reports_org on str_reports for all using (org_id = auth_org_id() or is_regulator());
create policy accounts_org on accounts for all using (org_id = auth_org_id() or is_regulator());
create policy transactions_org on transactions for all using (org_id = auth_org_id() or is_regulator());
create policy detection_runs_org on detection_runs for all using (org_id = auth_org_id() or is_regulator());
create policy alerts_org on alerts for all using (org_id = auth_org_id() or is_regulator());
create policy cases_org on cases for all using (org_id = auth_org_id() or is_regulator());
create policy rules_org on rules for all using (org_id = auth_org_id() or is_system = true);
create policy audit_org on audit_log for all using (org_id = auth_org_id());
create policy shared_entities on entities for all using (auth.uid() is not null);
create policy shared_connections on connections for all using (auth.uid() is not null);
create policy shared_matches on matches for all using (auth.uid() is not null);

create or replace function update_timestamp() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger organizations_updated before update on organizations for each row execute function update_timestamp();
create trigger entities_updated before update on entities for each row execute function update_timestamp();
create trigger str_reports_updated before update on str_reports for each row execute function update_timestamp();
create trigger alerts_updated before update on alerts for each row execute function update_timestamp();
create trigger cases_updated before update on cases for each row execute function update_timestamp();
create trigger rules_updated before update on rules for each row execute function update_timestamp();

create sequence if not exists case_ref_seq start 1;
create sequence if not exists str_ref_seq start 1;

create or replace function gen_case_ref() returns trigger as $$
begin
  new.case_ref = 'KST-' || to_char(now(),'YYMM') || '-' || lpad(nextval('case_ref_seq')::text, 5, '0');
  return new;
end;
$$ language plpgsql;

create or replace function gen_str_ref() returns trigger as $$
begin
  if new.report_ref is null or new.report_ref = '' then
    new.report_ref = 'STR-' || to_char(now(),'YYMM') || '-' || lpad(nextval('str_ref_seq')::text, 6, '0');
  end if;
  return new;
end;
$$ language plpgsql;

create trigger case_ref_trigger before insert on cases for each row execute function gen_case_ref();
create trigger str_ref_trigger before insert on str_reports for each row execute function gen_str_ref();

create or replace function handle_new_user() returns trigger as $$
begin
  insert into profiles (id, org_id, full_name, role, persona, designation)
  values (
    new.id,
    (new.raw_user_meta_data->>'org_id')::uuid,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)),
    coalesce(new.raw_user_meta_data->>'role', 'analyst'),
    coalesce(new.raw_user_meta_data->>'persona', 'bfiu_analyst'),
    new.raw_user_meta_data->>'designation'
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_signup after insert on auth.users for each row execute function handle_new_user();
