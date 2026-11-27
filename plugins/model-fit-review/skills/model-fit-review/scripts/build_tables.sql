-- Helper tables for a T3 Code state DB snapshot. They are TEMP tables, so the
-- snapshot file is not changed and it can be opened read-only:
--   sqlite3 "file:<snapshot>?mode=ro" -cmd ".read build_tables.sql" "select count(*) from hmsg"
-- extract_t3.py runs this file itself.

-- hmsg: human messages only, with the provider of the run they are attached
-- to. Other role='user' rows are delegation results, notices, messages from
-- other sessions (createdBy <> 'user', or creationSource 'provider'/'mcp'),
-- and answers to question prompts (creationSource 'server', table answers).
create temp table if not exists hmsg as
  select m.message_id id, m.thread_id thread, m.run_id, m.created_at at,
         json_extract(m.payload_json, '$.text') text, r.provider
  from orchestration_v2_projection_messages m
  left join orchestration_v2_projection_runs r on r.run_id = m.run_id
  where m.role = 'user'
    and json_extract(m.payload_json, '$.createdBy') = 'user'
    and json_extract(m.payload_json, '$.creationSource') in ('web', 'mobile');
create index if not exists temp.hmsg_i on hmsg(thread, at);
create index if not exists temp.hmsg_r on hmsg(run_id, at);

-- answers: a person's answer to an agent's question prompt. Counted, never
-- used as a reaction, steer or request (see lessons.md).
create temp table if not exists answers as
  select m.message_id id, m.thread_id thread, m.run_id, m.created_at at
  from orchestration_v2_projection_messages m
  where m.role = 'user'
    and json_extract(m.payload_json, '$.createdBy') = 'user'
    and json_extract(m.payload_json, '$.creationSource') = 'server';

-- truns: the timeline. One row per completed run of any provider, human- or
-- agent-initiated. first_user_by is createdBy of the run's earliest
-- role='user' message ('user' for a person; 'agent' for a delegation result
-- or notice); a run with no user message at all is agent-initiated.
create temp table if not exists truns as
  select r.run_id, r.thread_id thread, r.provider, r.requested_at, r.completed_at,
         json_extract(r.payload_json, '$.modelSelection.model') model,
         (select json_extract(j.value, '$.value')
            from json_each(json_extract(r.payload_json, '$.modelSelection.options')) j
           where json_extract(j.value, '$.id') = 'effort') effort,
         (select json_extract(u.payload_json, '$.createdBy') || '|' ||
                 coalesce(json_extract(u.payload_json, '$.creationSource'), '')
            from orchestration_v2_projection_messages u
           where u.run_id = r.run_id and u.role = 'user'
           order by u.created_at, u.message_id limit 1) first_user,
         (select json_extract(u.payload_json, '$.text')
            from orchestration_v2_projection_messages u
           where u.run_id = r.run_id and u.role = 'user'
           order by u.created_at, u.message_id limit 1) first_text,
         (select json_extract(a.payload_json, '$.text')
            from orchestration_v2_projection_messages a
           where a.run_id = r.run_id and a.role = 'assistant'
           order by a.created_at desc limit 1) reply_end
  from orchestration_v2_projection_runs r
  where r.status = 'completed' and r.completed_at is not null;
create index if not exists temp.truns_t on truns(thread, completed_at);

-- native: T3 thread <-> Claude Code session file. nativeThreadRef.nativeId is
-- the session file name (<nativeId>.jsonl). One T3 thread can have several.
create temp table if not exists native as
  select json_extract(payload_json, '$.nativeThreadRef.nativeId') native_id, thread_id thread
  from orchestration_v2_projection_provider_threads
  where provider like 'claude%' and json_extract(payload_json, '$.nativeThreadRef.nativeId') is not null;
