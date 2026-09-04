create table if not exists password_resets (
  id text primary key,
  email text not null,
  code_hash text not null,
  expires_at timestamptz not null,
  used boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists password_resets_email_idx on password_resets (email);
