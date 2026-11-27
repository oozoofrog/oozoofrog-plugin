-- Helper tables for a T3 Code state DB snapshot. They are TEMP tables, so the
-- snapshot file is not changed and it can be opened read-only:
--   sqlite3 "file:<snapshot>?mode=ro" -cmd ".read build_tables.sql" "select count(*) from hmsg"
-- extract_t3.py runs this file itself.

-- hmsg: human messages only. Other role='user' rows are delegation results,
-- notices and messages from other sessions.
create temp table if not exists hmsg as
  select message_id id, thread_id thread, run_id, created_at at,
         json_extract(payload_json, '$.text') text
  from orchestration_v2_projection_messages
  where role = 'user'
    and json_extract(payload_json, '$.createdBy') = 'user'
    and json_extract(payload_json, '$.creationSource') in ('web', 'mobile');
create index if not exists temp.hmsg_i on hmsg(thread, at);

-- hruns: one row per (completed Claude run, human message attached to it).
-- A run can carry several human messages; mfrlib.assign_reactions merges them.
create temp table if not exists hruns as
  select r.run_id, r.thread_id thread,
         json_extract(r.payload_json, '$.modelSelection.model') model,
         (select json_extract(j.value, '$.value')
            from json_each(json_extract(r.payload_json, '$.modelSelection.options')) j
           where json_extract(j.value, '$.id') = 'effort') effort,
         r.completed_at, h.id msg_id, h.at msg_at, h.text msg_text,
         (select json_extract(a.payload_json, '$.text')
            from orchestration_v2_projection_messages a
           where a.run_id = r.run_id and a.role = 'assistant'
           order by a.created_at desc limit 1) reply_end
  from orchestration_v2_projection_runs r join hmsg h on h.run_id = r.run_id
  where r.provider = 'claudeAgent' and r.status = 'completed';
