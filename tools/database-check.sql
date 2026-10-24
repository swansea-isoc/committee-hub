\set ON_ERROR_STOP on
-- Disposable CI database only. These roles/buckets stand in for Supabase's built-in scaffolding.
create role anon; create role authenticated; create role service_role bypassrls; create role supabase_auth_admin;
create schema storage;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
\i server/schema.sql
insert into public.hub3_members(id,email,name,role,finance,president) values
('11111111-1111-4111-8111-111111111111','owner@example.test','Test Gen Sec','admin',true,false),
('22222222-2222-4222-8222-222222222222','exec@example.test','Test Exec','exec',false,false),
('33333333-3333-4333-8333-333333333333','member@example.test','Test Member','member',false,false),
('44444444-4444-4444-8444-444444444444','president@example.test','Test President','exec',false,true);
insert into public.hub3_tasks(id,title,owner,creator,team,due) values
('55555555-5555-4555-8555-555555555555','Test action','33333333-3333-4333-8333-333333333333','22222222-2222-4222-8222-222222222222','Charity',now()+interval '8 days');
do $$begin
 if (select count(*) from public.hub3_outbox where event='assignment')<>1 then raise exception 'Assignment notification missing';end if;
 if exists(select from public.hub3_outbox where event='assignment' and member_id<>'33333333-3333-4333-8333-333333333333')then raise exception 'Wrong assignment recipient';end if;
end $$;
insert into public.hub3_reminders(id,task_id,member_id,kind,offset_hours,next_at) values
('66666666-6666-4666-8666-666666666666','55555555-5555-4555-8555-555555555555','33333333-3333-4333-8333-333333333333','before',168,now()-interval '1 minute');
select public.hub3_prepare_reminders(); select public.hub3_prepare_reminders();
do $$begin if(select count(*) from public.hub3_outbox where event='reminder')<>1 then raise exception 'Reminder duplicated';end if;end $$;
select public.hub3_update_task('55555555-5555-4555-8555-555555555555',1,'{"status":"Done"}','33333333-3333-4333-8333-333333333333','Finished');
do $$begin
 if not exists(select from public.hub3_outbox where event='completion' and member_id='22222222-2222-4222-8222-222222222222')then raise exception 'Completion not sent to assigning exec';end if;
 if exists(select from public.hub3_reminders where active)then raise exception 'Done reminder still active';end if;
 if exists(select from public.hub3_outbox where event='reminder' and status='pending')then raise exception 'Done reminder remains queued';end if;
 if (select count(*) from public.hub3_comments)<>1 then raise exception 'Comment not committed';end if;
 begin perform public.hub3_update_task('55555555-5555-4555-8555-555555555555',1,'{"status":"Blocked"}','33333333-3333-4333-8333-333333333333','Stale');raise exception 'Missed conflict';exception when others then if SQLERRM<>'TASK_CONFLICT' then raise;end if;end;
end $$;
-- Reassignment cancels the old owner's reminder and does not lose the new assignment event.
select public.hub3_update_task('55555555-5555-4555-8555-555555555555',2,'{"status":"To do","owner":"11111111-1111-4111-8111-111111111111"}','22222222-2222-4222-8222-222222222222','Reassigned');
do $$begin if not exists(select from public.hub3_outbox where event='assignment' and status='pending' and member_id='11111111-1111-4111-8111-111111111111')then raise exception 'New assignment cancelled incorrectly';end if;end $$;
insert into public.hub3_feedback(recipient,topic,message) values('president','Test concern','This is a disposable test message.');
do $$begin if (select count(*) from public.hub3_outbox where event='wellbeing')<>1 or exists(select from public.hub3_outbox where event='wellbeing' and member_id<>'44444444-4444-4444-8444-444444444444')then raise exception 'President message leaked';end if;end $$;
insert into public.hub3_files(id,owner_id,name,kind,scope,mime,size,path,status)values('77777777-7777-4777-8777-777777777777','33333333-3333-4333-8333-333333333333','Receipt.pdf','file','receipt','application/pdf',100,'dummy/test.pdf','ready');
insert into public.hub3_claims(requester_id,event,items,category,amount_pence,payment_ciphertext,receipt_id) values('33333333-3333-4333-8333-333333333333','Test event','Printing','Printing',500,'{"version":1,"cipher":"test"}','77777777-7777-4777-8777-777777777777');
do $$begin
 if (select count(*) from public.hub3_outbox where event='claim')<>1 or exists(select from public.hub3_outbox where event='claim' and member_id<>'11111111-1111-4111-8111-111111111111')then raise exception 'Claim notification not finance-only';end if;
 if has_table_privilege('anon','public.hub3_tasks','SELECT')or has_table_privilege('authenticated','public.hub3_claims','SELECT')or has_function_privilege('authenticated','public.hub3_update_task(uuid,integer,jsonb,uuid,text)','EXECUTE')then raise exception 'Browser DB access incorrectly granted';end if;
 if exists(select from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname like 'hub3_%' and c.relkind='r' and not c.relrowsecurity)then raise exception 'RLS not enabled';end if;
 if exists(select from storage.buckets where public)then raise exception 'Bucket is public';end if;
end $$;
-- Agent leasing prevents another worker picking the same pending mail. No automatically repeated ambiguous sends.
create temp table first_claim as select * from public.hub3_claim_emails(20);
create temp table second_claim as select * from public.hub3_claim_emails(20);
do $$begin if (select count(*) from second_claim)<>0 then raise exception 'Mail lease duplicated';end if;if exists(select from first_claim where lease is null)then raise exception 'Lease missing';end if;end $$;
select 'PASS: migration, permissions, task events, revision conflicts, reminder cancellation, mail leases, finance and feedback isolation' as result;
