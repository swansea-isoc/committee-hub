-- Committee Hub V3: a NEW dedicated private Supabase project, not either discount directory.
-- No real emails, names, banking details or records are seeded by this migration.
begin;
create table public.hub3_members (
 id uuid primary key default gen_random_uuid(), email text not null unique check(email=lower(email)), auth_user_id uuid unique,
 name text not null, title text not null default '', team text not null default 'Exec', role text not null default 'member' check(role in ('member','exec','admin')),
 finance boolean not null default false, media boolean not null default false, president boolean not null default false,
 about text not null default '', active boolean not null default true, created_at timestamptz not null default now(),
 check(not president or role in ('exec','admin'))
);
create table public.hub3_resources(key text primary key,url text not null check(url ~ '^https://'));
create table public.hub3_tasks (
 id uuid primary key default gen_random_uuid(), title text not null check(length(title) between 1 and 200), description text not null default '',
 owner uuid not null references public.hub3_members(id), creator uuid not null references public.hub3_members(id), team text not null,
 due timestamptz not null, priority text not null default 'Normal' check(priority in ('Low','Normal','High')),
 status text not null default 'To do' check(status in ('To do','In progress','For review','Done','Blocked')), blocker text not null default '',
 revision integer not null default 1, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table public.hub3_comments(id uuid primary key default gen_random_uuid(),task_id uuid not null references public.hub3_tasks(id) on delete cascade,member_id uuid not null references public.hub3_members(id),message text not null check(length(message) between 1 and 2000),created_at timestamptz not null default now());
create table public.hub3_reminders(id uuid primary key default gen_random_uuid(),task_id uuid not null references public.hub3_tasks(id) on delete cascade,member_id uuid not null references public.hub3_members(id),kind text not null check(kind in ('before','once','daily','weekly')),offset_hours integer,next_at timestamptz not null,active boolean not null default true,created_at timestamptz not null default now());
create table public.hub3_media(id uuid primary key default gen_random_uuid(),title text not null,team text not null,format text not null,brief text not null,needed_by timestamptz not null,asset_url text not null default '',requester_id uuid references public.hub3_members(id),requester_name text not null default '',external_key text unique,status text not null default 'New' check(status in ('New','In progress','Ready')),revision integer not null default 1,created_at timestamptz not null default now());
create table public.hub3_files(id uuid primary key default gen_random_uuid(),parent uuid references public.hub3_files(id),owner_id uuid not null references public.hub3_members(id),name text not null,kind text not null check(kind in ('file','folder')),scope text not null check(scope in ('shared','receipt')),mime text not null default '',size bigint not null default 0,path text unique,status text not null default 'uploading' check(status in ('uploading','ready')),created_at timestamptz not null default now());
create table public.hub3_claims(id uuid primary key default gen_random_uuid(),requester_id uuid not null references public.hub3_members(id),event text not null,items text not null,category text not null,amount_pence integer not null check(amount_pence between 1 and 500000),payment_ciphertext jsonb not null,receipt_id uuid not null references public.hub3_files(id),status text not null default 'Awaiting review' check(status in ('Awaiting review','Need information','Approved','Paid','Declined')),revision integer not null default 1,created_at timestamptz not null default now());
-- Deliberately no sender, email, session identifier or precise submission time on feedback.
create table public.hub3_feedback(id uuid primary key default gen_random_uuid(),recipient text not null check(recipient in ('president','exec')),topic text not null check(length(topic) between 1 and 100),message text not null check(length(message) between 5 and 4000),day date not null default (now() at time zone 'Europe/London')::date);
create table public.hub3_limits(bucket text primary key,hits integer not null default 1,expires_at timestamptz not null);
create table public.hub3_outbox(id uuid primary key default gen_random_uuid(),member_id uuid not null references public.hub3_members(id),event text not null,record_id uuid,subject text not null,dedupe text unique not null,status text not null default 'pending' check(status in ('pending','sending','sent','failed','cancelled')),attempts integer not null default 0,available_at timestamptz not null default now(),locked_at timestamptz,lease uuid,provider_id text,last_error text,read_at timestamptz,created_at timestamptz not null default now());
create index on public.hub3_tasks(owner,status,due);create index on public.hub3_reminders(next_at) where active;create index on public.hub3_files(parent,scope,status);create index on public.hub3_claims(requester_id,created_at);create index on public.hub3_outbox(status,available_at);create index on public.hub3_outbox(member_id,created_at);
-- No direct browser/PostgREST access to ANY hub table. The Edge API authorises every operation.
do $$ declare t text; begin foreach t in array array['members','resources','tasks','comments','reminders','media','files','claims','feedback','limits','outbox'] loop
 execute format('alter table public.hub3_%I enable row level security',t);
 execute format('revoke all on public.hub3_%I from public,anon,authenticated',t);
 execute format('grant all on public.hub3_%I to service_role',t);
end loop; end $$;
-- Optional Auth before-user-created hook; the API allowlist still applies on every call.
create function public.hub3_before_user_created(event jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from public.hub3_members where active and email=lower(event->'user'->>'email')) then
 return jsonb_build_object('error',jsonb_build_object('http_code',403,'message','This Google account is not approved for committee access.'));end if;
 return '{}'::jsonb;
end; $$;
revoke all on function public.hub3_before_user_created(jsonb) from public,anon,authenticated;
grant execute on function public.hub3_before_user_created(jsonb) to supabase_auth_admin;
create function public.hub3_rate_limit(p_bucket text,p_limit integer,p_expiry timestamptz) returns boolean language plpgsql security definer set search_path='' as $$
declare n integer;begin
 insert into public.hub3_limits(bucket,hits,expires_at) values(p_bucket,1,p_expiry)
 on conflict(bucket) do update set hits=public.hub3_limits.hits+1 returning hits into n;
 return n<=p_limit;
end; $$;
create function public.hub3_enqueue(p_member uuid,p_event text,p_record uuid,p_subject text,p_key text) returns void language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from public.hub3_members where id=p_member and active) then
 insert into public.hub3_outbox(member_id,event,record_id,subject,dedupe) values(p_member,p_event,p_record,p_subject,p_key) on conflict(dedupe) do nothing;
 end if;
end; $$;
-- Atomic assignment/completion notifications and reminder cancellation accompany task writes.
create function public.hub3_task_event() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if TG_OP='INSERT' then
  perform public.hub3_enqueue(new.owner,'assignment',new.id,'An action point has been assigned to you','assign/'||new.id||'/'||new.revision);
 else
  if new.owner is distinct from old.owner then
   perform public.hub3_enqueue(new.owner,'assignment',new.id,'An action point has been assigned to you','assign/'||new.id||'/'||new.revision);
   update public.hub3_reminders set active=false where task_id=new.id;
   update public.hub3_outbox set status='cancelled' where record_id=new.id and event in ('assignment','reminder') and status='pending';
   -- Preserve the new assignment notice (the cancellation above also matches it).
   update public.hub3_outbox set status='pending' where dedupe='assign/'||new.id||'/'||new.revision;
  end if;
  if new.due is distinct from old.due then
   update public.hub3_reminders set next_at=greatest(new.due-offset_hours*interval '1 hour',now()) where task_id=new.id and kind='before' and active;
  end if;
  if new.status='Done' and old.status is distinct from 'Done' then
   if exists(select 1 from public.hub3_members where id=new.creator and role in ('exec','admin') and active) then
    perform public.hub3_enqueue(new.creator,'completion',new.id,'An action point you assigned is complete','done/'||new.id||'/'||new.revision);
   end if;
   update public.hub3_reminders set active=false where task_id=new.id;
   update public.hub3_outbox set status='cancelled' where record_id=new.id and event in ('assignment','reminder') and status='pending';
  end if;
 end if;
 return new;
end; $$;
create trigger hub3_task_notifications after insert or update on public.hub3_tasks for each row execute function public.hub3_task_event();
create function public.hub3_request_event() returns trigger language plpgsql security definer set search_path='' as $$
declare m record;begin
 if TG_TABLE_NAME='hub3_media' then
  if TG_OP='INSERT' then for m in select id from public.hub3_members where active and (media or role in ('exec','admin')) loop perform public.hub3_enqueue(m.id,'media',new.id,'A new media request needs your team','media/'||new.id||'/'||m.id);end loop;
  elsif new.status is distinct from old.status and new.requester_id is not null then perform public.hub3_enqueue(new.requester_id,'media-progress',new.id,'Your media request has an update','media-progress/'||new.id||'/'||new.revision);end if;
 elsif TG_TABLE_NAME='hub3_claims' then
  if TG_OP='INSERT' then for m in select id from public.hub3_members where active and finance loop perform public.hub3_enqueue(m.id,'claim',new.id,'A reimbursement request needs review','claim/'||new.id||'/'||m.id);end loop;
  elsif new.status is distinct from old.status then perform public.hub3_enqueue(new.requester_id,'claim-progress',new.id,'Your reimbursement request has an update','claim-progress/'||new.id||'/'||new.revision);end if;
 elsif TG_TABLE_NAME='hub3_feedback' then
  for m in select id from public.hub3_members where active and role in ('exec','admin') and (new.recipient='exec' or president) loop
   perform public.hub3_enqueue(m.id,'wellbeing',new.id,'A private committee message is ready to read','wellbeing/'||new.id||'/'||m.id);
  end loop;
 end if;return new;
end; $$;
create trigger hub3_media_notifications after insert or update on public.hub3_media for each row execute function public.hub3_request_event();
create trigger hub3_claim_notifications after insert or update on public.hub3_claims for each row execute function public.hub3_request_event();
create trigger hub3_feedback_notifications after insert on public.hub3_feedback for each row execute function public.hub3_request_event();
-- Transactional task + comment save; revision comparison prevents overwriting another person's change.
create function public.hub3_update_task(p_id uuid,p_revision integer,p_patch jsonb,p_actor uuid,p_comment text) returns public.hub3_tasks language plpgsql security definer set search_path='' as $$
declare t public.hub3_tasks;begin
 select * into t from public.hub3_tasks where id=p_id for update;
 if t.id is null or t.revision<>p_revision then raise exception 'TASK_CONFLICT';end if;
 update public.hub3_tasks set title=coalesce(p_patch->>'title',title),owner=coalesce((p_patch->>'owner')::uuid,owner),due=coalesce((p_patch->>'due')::timestamptz,due),status=coalesce(p_patch->>'status',status),blocker=coalesce(p_patch->>'blocker',blocker),revision=revision+1,updated_at=now() where id=p_id returning * into t;
 if coalesce(p_comment,'')<>'' then insert into public.hub3_comments(task_id,member_id,message) values(p_id,p_actor,p_comment);end if;
 return t;
end; $$;
-- Called by a secret-protected scheduler, never the browser. Uses row locks for concurrent workers.
create function public.hub3_prepare_reminders() returns integer language plpgsql security definer set search_path='' as $$
declare r record;t record;m record;n integer:=0;begin
 for r in select * from public.hub3_reminders where active and next_at<=now() order by next_at for update skip locked limit 100 loop
  select * into t from public.hub3_tasks where id=r.task_id;select * into m from public.hub3_members where id=r.member_id;
  if t.id is null or t.status='Done' or not m.active or (m.role='member' and t.owner<>m.id) then update public.hub3_reminders set active=false where id=r.id;continue;end if;
  perform public.hub3_enqueue(r.member_id,'reminder',r.task_id,'Reminder: you have a committee action to review','reminder/'||r.id||'/'||extract(epoch from r.next_at));n:=n+1;
  if r.kind in ('before','once') then update public.hub3_reminders set active=false where id=r.id;
  else update public.hub3_reminders set next_at=now()+case when r.kind='daily' then interval '24 hours' else interval '168 hours' end where id=r.id;end if;
 end loop;delete from public.hub3_limits where expires_at<now();return n;
end; $$;
create function public.hub3_claim_emails(p_limit integer default 10) returns setof public.hub3_outbox language plpgsql security definer set search_path='' as $$
begin
 -- Never automatically resend an ambiguous send; an interrupted agent needs administrator review.
 update public.hub3_outbox set status='failed',last_error='Unacknowledged send; check mailbox before retrying' where status='sending' and locked_at<now()-interval '30 minutes';
 return query with picked as (select id from public.hub3_outbox where status='pending' and available_at<=now() and attempts<5 order by created_at for update skip locked limit least(p_limit,20))
 update public.hub3_outbox o set status='sending',locked_at=now(),lease=gen_random_uuid(),attempts=o.attempts+1 from picked where o.id=picked.id returning o.*;
end; $$;
-- Routine permissions: service-only, never callable by public users directly.
do $$ declare p record;begin for p in select n.nspname,pr.proname,pg_get_function_identity_arguments(pr.oid) args from pg_proc pr join pg_namespace n on n.oid=pr.pronamespace where n.nspname='public' and pr.proname like 'hub3_%' and pr.proname<>'hub3_before_user_created' loop
 execute format('revoke all on function %I.%I(%s) from public,anon,authenticated',p.nspname,p.proname,p.args);
 execute format('grant execute on function %I.%I(%s) to service_role',p.nspname,p.proname,p.args);
end loop;end $$;
-- PRIVATE storage. Browser upload tokens are minted only after an approved member passes the API checks.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values
('committee-files','committee-files',false,20971520,array['application/pdf','image/png','image/jpeg','image/webp','application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','application/vnd.openxmlformats-officedocument.presentationml.presentation','text/plain','text/csv','video/mp4','audio/mpeg']),
('committee-receipts','committee-receipts',false,20971520,array['application/pdf','image/png','image/jpeg','image/webp'])
on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit,allowed_mime_types=excluded.allowed_mime_types;
commit;
