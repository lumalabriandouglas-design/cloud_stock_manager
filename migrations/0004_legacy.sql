-- Mapping + leftover Django hashes. Never drop inventory_* or auth_user.
create table if not exists legacy_credentials (
  username text primary key,
  email text not null default '',
  django_password text not null,
  is_superuser boolean not null default false,
  auth_user_id text not null
);

create table if not exists legacy_import_state (
  id text primary key,
  imported_at timestamptz not null default now(),
  companies integer not null default 0,
  users integer not null default 0,
  items integer not null default 0
);
