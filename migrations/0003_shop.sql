create table if not exists companies (
  id text primary key,
  name text not null,
  owner_user_id text not null,
  created_at timestamptz not null default now()
);

create index if not exists companies_owner_idx on companies (owner_user_id);

create table if not exists subscriptions (
  id text primary key,
  company_id text not null unique references companies (id) on delete cascade,
  status text not null default 'trial',
  trial_ends_at timestamptz,
  current_period_end timestamptz,
  last_payment_at timestamptz,
  payment_phone text not null default '',
  payment_tx_id text not null default '',
  payment_note text not null default '',
  payment_claimed_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists memberships (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  user_id text not null,
  email text not null default '',
  name text not null default '',
  role text not null default 'staff',
  can_manage_stock boolean not null default true,
  can_edit_items boolean not null default true,
  can_view_reports boolean not null default true,
  can_manage_categories boolean not null default false,
  can_manage_team boolean not null default false,
  created_at timestamptz not null default now(),
  unique (company_id, user_id)
);

create index if not exists memberships_user_idx on memberships (user_id);

create table if not exists invites (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  email text not null,
  role text not null default 'staff',
  can_manage_stock boolean not null default true,
  can_edit_items boolean not null default true,
  can_view_reports boolean not null default true,
  can_manage_categories boolean not null default false,
  can_manage_team boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists platform_admins (
  user_id text primary key,
  email text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists categories (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  name text not null
);

create table if not exists items (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  name text not null,
  category_id text,
  buy_price integer not null default 0,
  sell_price integer not null default 0,
  quantity integer not null default 0,
  reorder_level integer not null default 5
);

create table if not exists sales (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  item_id text,
  item_name text not null,
  quantity integer not null,
  sell_price integer not null,
  cost_price integer not null,
  created_at timestamptz not null default now()
);

create index if not exists sales_company_idx on sales (company_id, created_at);

create table if not exists stock_moves (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  item_id text,
  item_name text not null,
  quantity integer not null,
  created_at timestamptz not null default now()
);

create table if not exists activities (
  id text primary key,
  company_id text not null references companies (id) on delete cascade,
  kind text not null,
  message text not null,
  created_at timestamptz not null default now()
);
