"""Read-only collaboration doctor; JSON recovery plans are executed by the coordinator."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

if sys.version_info < (3, 11):
    raise SystemExit('Collaboration doctor requires Python 3.11 or later.')
import tomllib

PLUGIN = 'codex-app-tools@openai-bundled'
TOOLS = ('create_thread', 'send_message_to_thread', 'fork_thread',
         'handoff_thread', 'move_thread_to_project', 'automation_update')
MEMBER_ROLES = {'core', 'support', 'advisor', 'reviewer', 'bootstrap'}
USER_INPUT_TOOLS = {'request_user_input', 'request_user_input_async'}
LEGACY_PACKET_TEXT = ('no destination-specific human authorization',
                      'do not send any follow-up message',
                      'ask the user for permission before messaging')
QUESTION_CANDIDATES = ('may i ', 'should i ', 'please approve', 'please confirm',
                       'do you approve', 'would you like me to', 'can i send',
                       '승인해 주', '승인해주', '승인하시겠', '진행할까요',
                       '계속할까요', '허가해 주', '선택해 주', '선택해주')


def mapping(value):
    return value if isinstance(value, dict) else {}


def mode_value(value):
    return value if isinstance(value, str) and value in ('approve', 'prompt', 'deny', 'unknown') else 'unsupported'


def response(record):
    value = mapping(record.get('response', record.get('result', {})))
    if value.get('isError') is True:
        return {'_tool_error': True}
    if isinstance(value.get('structuredContent'), dict):
        return value['structuredContent']
    if isinstance(value.get('content'), list):
        texts = [item.get('text', '') for item in value['content']
                 if isinstance(item, dict) and item.get('type') == 'text']
        if len(texts) == 1:
            try:
                return mapping(json.loads(texts[0]))
            except (ValueError, TypeError):
                return {}
    return value


def text_content(item):
    if isinstance(item.get('text'), str):
        return item['text']
    return '\n'.join(part.get('text', '') for part in item.get('content', [])
                     if isinstance(part, dict) and part.get('type') == 'text')


class Report:
    def __init__(self):
        self.findings = []
        self.actions = []

    def finding(self, code, severity, message, **evidence):
        value = dict(code=code, severity=severity, message=message, **evidence)
        if value not in self.findings:
            self.findings.append(value)

    def action(self, kind, **details):
        value = dict(kind=kind, retry=False, requires_human_prompt=False, **details)
        if value not in self.actions:
            self.actions.append(value)


def inspect_policy(config, app_policy, report):
    plugin = mapping(mapping(config.get('plugins')).get(PLUGIN))
    server = mapping(mapping(plugin.get('mcp_servers')).get('codex_app'))
    manifest = mapping(mapping(app_policy.get('mcpServers')).get('codex_app'))
    user_tools, manifest_tools = mapping(server.get('tools')), mapping(manifest.get('tools'))
    tools = {}
    for name in TOOLS:
        user, declared = mapping(user_tools.get(name)), mapping(manifest_tools.get(name))
        if 'approval_mode' in user:
            mode, source = user['approval_mode'], 'user_tool_override'
        elif 'approval_mode' in declared:
            mode, source = declared['approval_mode'], 'plugin_tool_policy'
        elif 'default_tools_approval_mode' in server:
            mode, source = server['default_tools_approval_mode'], 'user_server_default'
        elif 'default_tools_approval_mode' in manifest:
            mode, source = manifest['default_tools_approval_mode'], 'plugin_server_default'
        else:
            mode, source = 'unknown', 'unobserved'
        layers = {'user_tool': mode_value(user['approval_mode']) if 'approval_mode' in user else None,
                  'plugin_tool': mode_value(declared['approval_mode']) if 'approval_mode' in declared else None,
                  'user_default': mode_value(server['default_tools_approval_mode']) if 'default_tools_approval_mode' in server else None,
                  'plugin_default': mode_value(manifest['default_tools_approval_mode']) if 'default_tools_approval_mode' in manifest else None}
        mode = mode_value(mode)
        if ('approval_mode' not in user and 'approval_mode' in declared
                and 'default_tools_approval_mode' in server
                and declared['approval_mode'] != server['default_tools_approval_mode']):
            report.finding('POLICY_LAYER_CONFLICT', 'warning', 'Visible policy layers differ; verify the active client rather than claiming runtime precedence.', tool=name)
            report.action('verify_active_server_identity', tool=name)
        disabled = (plugin.get('enabled') is False or server.get('enabled') is False
                    or user.get('enabled') is False or name in server.get('disabled_tools', [])
                    or ('enabled_tools' in server and name not in server['enabled_tools']))
        tools[name] = {'configured_mode': mode, 'source': source, 'layers': layers, 'explicitly_disabled': disabled}
        if disabled:
            report.finding('COLLAB_TOOL_DISABLED', 'error', 'An explicit user tool filter disables collaboration.', tool=name)
            report.action('honor_explicit_restriction', tool=name)
        elif mode == 'prompt':
            report.finding('COLLAB_TOOL_REQUIRES_APPROVAL', 'warning', 'A configured tool policy requests approval.', tool=name, source=source)
            report.action('configure_tool_policy', tool=name,
                          key='plugins."'+PLUGIN+'".mcp_servers.codex_app.tools.'+name+'.approval_mode',
                          value='approve', condition='Current human task delegation permits this tool; one coordinator preserves other settings and restrictions.')
        elif mode not in ('approve', 'unknown'):
            report.finding('EXPLICIT_POLICY_RESTRICTION', 'error', 'An explicit restrictive or unknown mode must be preserved.', tool=name)
            report.action('honor_explicit_restriction', tool=name)
        elif mode == 'unknown':
            report.finding('TOOL_POLICY_UNOBSERVED', 'info', 'Obtain the installed plugin policy before deciding whether a setting is missing.', tool=name)
            report.action('observe_installed_tool_policy', tool=name)
    if 'codex_app' in mapping(config.get('mcp_servers')):
        report.finding('DUPLICATE_SERVER_CONFIGURATION', 'warning', 'A separate codex_app server configuration may differ from the plugin-provided server.')
        report.action('verify_active_server_identity')
    return tools


def valid_reads(snapshot, report):
    reads = {}
    for entry in snapshot.get('reads', []):
        if entry.get('source') != 'codex_app.read_thread':
            report.finding('EVIDENCE_SOURCE_UNSUPPORTED', 'warning', 'A read record lacks the supported source marker.')
            continue
        data = response(entry)
        requested = entry.get('requested_thread_id')
        observed = mapping(data.get('thread')).get('id')
        if not requested or requested != observed:
            report.finding('EVIDENCE_IDENTITY_MISMATCH', 'error', 'Requested and returned thread identities differ.', requested_thread_id=requested, observed_thread_id=observed)
            continue
        reads[requested] = data
    return reads


def inspect_team(snapshot, reads, report):
    team = mapping(snapshot.get('team'))
    members, known = {}, set()
    for member in team.get('members', []):
        identifier = member.get('thread_id')
        if not identifier:
            report.finding('TEAM_ID_MISSING', 'warning', 'A team member lacks a returned thread ID.')
            continue
        if identifier in known:
            report.finding('DUPLICATE_TEAM_ID', 'error', 'A team ID appears more than once.', thread_id=identifier)
        members[identifier] = member
        known.add(identifier)
    leader = team.get('leader_id')
    destination = leader or team.get('coordinator_id')
    if team and (not destination or (leader and leader not in known)):
        report.finding('DECISION_ROUTE_UNVERIFIED', 'warning', 'The team decision route is not bound to a verified team ID.', destination=destination)
        report.action('verify_existing_decision_route', destination=destination)
    for identifier, member in members.items():
        if member.get('role') in MEMBER_ROLES and not member.get('leader_id'):
            report.finding('MEMBER_DECISION_ROUTE_MISSING', 'warning', 'A member packet does not carry its decision route.', thread_id=identifier)
            report.action('refresh_role_packet', thread_id=identifier, destination=destination,
                          condition='Verify the current delegation and existing owner; refresh only a stale packet.')
    delegation = mapping(team.get('delegation'))
    observed, digest = False, None
    if team:
        source = reads.get(delegation.get('thread_id'), {})
        for turn in source.get('turns', []):
            if turn.get('id') != delegation.get('turn_id'):
                continue
            for item in turn.get('items', []):
                if item.get('id') == delegation.get('message_id') and item.get('type') == 'userMessage':
                    observed = True
                    digest = hashlib.sha256(text_content(item).encode()).hexdigest()
        if not observed:
            report.finding('DELEGATION_SOURCE_UNVERIFIED', 'warning', 'The referenced actual human message has not been observed.')
            report.action('verify_source_delegation', source_reference={
                key: delegation.get(key) for key in ('thread_id', 'turn_id', 'message_id')})
    return members, destination, {'human_message_observed': observed,
        'human_message_sha256': digest, 'semantic_authority_verified': False,
        'limit': 'The coordinator evaluates actual human scope; a copied agent claim is insufficient.'}


def inspect_threads(snapshot, reads, members, destination, tools, report):
    waiting = set()
    exact_pending = set()
    allowed = set(members)
    coordinator = mapping(snapshot.get('team')).get('coordinator_id')
    if coordinator:
        allowed.add(coordinator)
    for pending in snapshot.get('pending_requests', []):
        if (pending.get('source') != 'codex_app.read_thread' or not pending.get('request_id')
                or pending.get('state') != 'pending' or not pending.get('thread_id') or not pending.get('tool')):
            report.finding('PENDING_REQUEST_EVIDENCE_INCOMPLETE', 'warning', 'Pending-request evidence lacks an exact identity or supported source.')
            continue
        thread, tool = pending['thread_id'], pending['tool']
        if thread not in allowed:
            report.finding('EVIDENCE_OUTSIDE_TEAM', 'error', 'Pending-request evidence is outside the recorded team; no repair is proposed.', thread_id=thread)
            continue
        exact_pending.add(thread)
        if mapping(tools.get(tool)).get('configured_mode') == 'approve':
            report.finding('APPROVED_POLICY_PENDING_REQUEST', 'warning', 'Saved approve policy does not resolve an already-pending request or prove client adoption.', thread_id=thread, tool=tool, request_id=pending['request_id'])
        else:
            report.finding('EXACT_PENDING_REQUEST', 'warning', 'An exact pending request needs its supported resolution.', thread_id=thread, tool=tool, request_id=pending['request_id'])
        report.action('reconcile_exact_pending_request', thread_id=thread, tool=tool,
                      request_id=pending['request_id'], condition='Use an exposed supported resolution/reload at a safe boundary; do not forge approval, restart active producers or resubmit.')
    for identifier, data in reads.items():
        thread = mapping(data.get('thread'))
        status = mapping(thread.get('status'))
        if identifier in allowed and 'waitingOnApproval' in status.get('activeFlags', []):
            waiting.add(identifier)
        if identifier not in allowed:
            continue
        preview = str(thread.get('preview', '')).casefold()
        if identifier in members and any(phrase in preview for phrase in LEGACY_PACKET_TEXT):
            report.finding('STALE_MESSAGING_PACKET', 'warning', 'Legacy messaging restrictions remain in the initial packet; inspect any newer packet acknowledgement before refreshing.', thread_id=identifier)
            report.action('refresh_role_packet', thread_id=identifier, destination=destination,
                          condition='Only if current instructions remain stale; verify current human delegation, owner and previous dispatch outcome first.')
        turns = data.get('turns', [])
        latest = turns[0] if turns else {}
        error = str(mapping(latest.get('error')).get('message', '')).casefold()
        if 'at capacity' in error:
            report.finding('MODEL_CAPACITY_UNAVAILABLE', 'warning', 'The observed model-capacity failure is separate from permission policy.', thread_id=identifier)
            report.action('report_model_capacity', thread_id=identifier, condition='Keep the requested model; no silent substitute or duplicate run.')
        for item in latest.get('items', []):
            name = str(item.get('tool', item.get('name', ''))).split('.')[-1]
            failure = str(mapping(item.get('error')).get('message', '')).casefold()
            if item.get('status') == 'failed' and any(phrase in failure for phrase in (
                    'permission denied', 'approval denied', 'denied by user',
                    'user denied', 'approval review rejected', 'denied by policy')):
                report.finding('TOOL_PERMISSION_DENIED', 'error', 'An actual denial must be preserved; changing policy is not a retry workaround.', thread_id=identifier, tool=name, item_id=item.get('id'))
                report.action('honor_observed_denial', thread_id=identifier, tool=name)
            if members.get(identifier, {}).get('role') in MEMBER_ROLES and name in USER_INPUT_TOOLS:
                report.finding('MEMBER_DIRECT_USER_PROMPT', 'warning', 'A member used a human-input tool instead of the team decision route.', thread_id=identifier, item_id=item.get('id'))
                report.action('route_decision_to_leader', thread_id=identifier, destination=destination,
                              condition='Resolve from existing delegation/evidence; do not invent a human answer.')
            elif (members.get(identifier, {}).get('role') in MEMBER_ROLES
                  and item.get('type') == 'agentMessage'
                  and item.get('phase') in ('final_answer', 'final')
                  and any(phrase in text_content(item).casefold() for phrase in QUESTION_CANDIDATES)):
                report.finding('POSSIBLE_MEMBER_USER_QUESTION', 'warning', 'Final text may ask the human for a decision; inspect its recipient and distinguish quotations/internal messages.', thread_id=identifier, item_id=item.get('id'))
                report.action('review_question_recipient', thread_id=identifier, destination=destination,
                              condition='Only a confirmed human-facing request is rerouted; do not treat a quoted example or internal leader question as a new prompt.')
    for entry in snapshot.get('waits', []):
        if entry.get('source') != 'codex_app.wait_threads':
            report.finding('EVIDENCE_SOURCE_UNSUPPORTED', 'warning', 'A wait record lacks the supported source marker.')
            continue
        for poll in response(entry).get('polls', []):
            thread = mapping(poll.get('thread'))
            if 'waitingOnApproval' in mapping(thread.get('status')).get('activeFlags', []):
                if thread.get('id') in allowed:
                    waiting.add(thread['id'])
                else:
                    report.finding('EVIDENCE_OUTSIDE_TEAM', 'warning', 'A wait snapshot identifies a thread outside the recorded team.', thread_id=thread.get('id'))
    for identifier in sorted(waiting - exact_pending, key=str):
        report.finding('APPROVAL_WAIT_UNATTRIBUTED', 'warning', 'A generic waitingOnApproval flag does not identify a blocked command.', thread_id=identifier)
        report.action('collect_exact_pending_action', thread_id=identifier,
                      condition='Use bounded official read/status evidence. A completed last tool marker is not the pending action; do not guess or retry.')


def inspect_deliveries(snapshot, members, report):
    deliveries = []
    allowed = set(members)
    coordinator = mapping(snapshot.get('team')).get('coordinator_id')
    if coordinator:
        allowed.add(coordinator)
    for entry in snapshot.get('deliveries', []):
        requested, result = entry.get('requested_thread_id'), response(entry)
        if entry.get('source') != 'codex_app.send_message_to_thread':
            report.finding('EVIDENCE_SOURCE_UNSUPPORTED', 'warning', 'A delivery record lacks the supported source marker.')
            continue
        if requested not in allowed:
            report.finding('EVIDENCE_OUTSIDE_TEAM', 'error', 'A message receipt is outside the recorded team; no follow-up is proposed.', thread_id=requested)
            deliveries.append({'thread_id': requested, 'state': 'outside_team', 'acknowledged': False})
            continue
        returned = result.get('threadId')
        if returned and returned != requested:
            report.finding('DELIVERY_DESTINATION_MISMATCH', 'error', 'The message receipt identifies a different thread.', thread_id=requested)
            state = 'identity_mismatch'
        elif returned == requested and requested:
            state = 'submitted'
            report.action('observe_delivery_ack', thread_id=requested,
                          condition='Inspect actual recipient input/acknowledgement; submission alone is not completion and does not authorize a resend.')
        else:
            state = 'failed' if result.get('_tool_error') else 'unknown'
            report.finding('MESSAGE_DELIVERY_'+state.upper(), 'warning', 'Message outcome must be reconciled before another dispatch.', thread_id=requested)
            report.action('reconcile_delivery_outcome', thread_id=requested)
        deliveries.append({'thread_id': requested, 'state': state, 'acknowledged': False})
    return deliveries


def inspect_state(state, report):
    tasks = mapping(state.get('tasks'))
    active = [(key, value) for key, value in tasks.items()
              if isinstance(value, dict) and value.get('state') not in ('accepted', 'cancelled', 'released')]
    for index, (first, left) in enumerate(active):
        for second, right in active[index+1:]:
            if not left.get('owner') or not right.get('owner') or left['owner'] == right['owner']:
                continue
            overlap = False
            for a in left.get('paths', []):
                for b in right.get('paths', []):
                    try:
                        common = os.path.commonpath([a, b])
                        overlap |= common in (os.path.normpath(a), os.path.normpath(b))
                    except (TypeError, ValueError):
                        continue
            if overlap:
                report.finding('OWNERSHIP_CONFLICT', 'error', 'Different owners have overlapping declared active claims.', tasks=[first, second])
                report.action('coordinate_owner_boundary', tasks=[first, second],
                              condition='Use current owner evidence and the supported transfer/release protocol; do not edit ledger ownership directly.')
    for identifier, run in mapping(mapping(state.get('harness')).get('runs')).items():
        if mapping(run).get('state') == 'uncertain':
            report.finding('UNCERTAIN_PRODUCER', 'error', 'An uncertain producer blocks duplicate repair/dispatch.', run_id=identifier, member=run.get('member'))
            report.action('reconcile_producer_outcome', run_id=identifier)


def diagnose(config, *, app_policy=None, snapshot=None, state=None):
    report = Report()
    for name, value in (('config', config), ('app_policy', app_policy), ('snapshot', snapshot), ('state', state)):
        if value is not None and not isinstance(value, dict):
            report.finding('INVALID_INPUT_SHAPE', 'error', 'A supplied input must be an object.', input=name)
    tools = inspect_policy(mapping(config), mapping(app_policy), report)
    snapshot = mapping(snapshot)
    if snapshot and (type(snapshot.get('schema')) is not int or snapshot['schema'] != 1):
        report.finding('INVALID_SNAPSHOT_SCHEMA', 'error', 'Use collaboration evidence schema 1.')
        snapshot = {}
    reads = valid_reads(snapshot, report)
    members, destination, delegation = inspect_team(snapshot, reads, report)
    inspect_threads(snapshot, reads, members, destination, tools, report)
    deliveries = inspect_deliveries(snapshot, members, report)
    inspect_state(mapping(state), report)
    denied = {item.get('tool') for item in report.findings if item['code'] == 'TOOL_PERMISSION_DENIED'}
    report.actions = [action for action in report.actions
                      if not (action['kind'] == 'configure_tool_policy' and action.get('tool') in denied)]
    severity = {item['severity'] for item in report.findings}
    if 'error' in severity:
        status = 'blocked'
    elif 'warning' in severity:
        status = 'needs_attention'
    elif snapshot:
        status = 'observed_no_collaboration_blocker'
    elif all(value['configured_mode'] == 'approve' for value in tools.values()):
        status = 'configured_runtime_unverified'
    else:
        status = 'insufficient_policy_evidence'
    return {'schema': 1, 'read_only': True, 'status': status, 'runtime_verified': False,
            'tools': tools, 'delegation': delegation, 'deliveries': deliveries,
            'coverage': {'installed_policy_supplied': app_policy is not None,
                         'project_state_supplied': state is not None,
                         'matched_thread_reads': len(reads),
                         'unobserved_member_ids': sorted(set(members)-set(reads)),
                         'wait_records': len(snapshot.get('waits', [])),
                         'delivery_records': len(deliveries),
                         'pending_request_records': len(snapshot.get('pending_requests', []))},
            'findings': report.findings, 'recovery_plan': report.actions,
            'evidence_limits': ['Snapshots are operator-supplied public-tool records, not authenticated live queries.',
                'Configured policy, recipient acknowledgement and native popup absence are separate evidence.',
                'Recovery actions require current task authority and supported client controls; this command writes no configuration, state or approvals.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    home = Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))
    parser.add_argument('--config', type=Path, default=home/'config.toml')
    parser.add_argument('--app-policy', type=Path, help='Observed installed codex-app-tools .mcp.json')
    parser.add_argument('--snapshot', type=Path, help='Schema-1 official-tool evidence snapshot')
    parser.add_argument('--state', type=Path, help='Existing project ledger, read only')
    args = parser.parse_args()
    try:
        config = tomllib.loads(args.config.read_text(encoding='utf-8')) if args.config.exists() else {}
        load = lambda path: json.loads(path.read_text(encoding='utf-8')) if path else None
        result = diagnose(config, app_policy=load(args.app_policy), snapshot=load(args.snapshot), state=load(args.state))
    except (OSError, ValueError, TypeError, AttributeError):
        result = {'schema': 1, 'read_only': True, 'status': 'blocked', 'runtime_verified': False,
                  'findings': [{'code': 'INPUT_UNREADABLE_OR_INVALID', 'severity': 'error',
                                'message': 'An explicitly supplied input is unreadable or has invalid syntax/shape.'}],
                  'recovery_plan': [{'kind': 'reconcile_input_evidence', 'retry': False, 'requires_human_prompt': False}]}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result['status'] == 'blocked' else (2 if result['status'] in ('needs_attention', 'insufficient_policy_evidence') else 0)


if __name__ == '__main__':
    raise SystemExit(main())
