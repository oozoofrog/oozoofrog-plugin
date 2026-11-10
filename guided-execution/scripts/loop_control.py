#!/usr/bin/env python3
"""Record single-writer coordinator transitions; never execute project commands.

Only record integrity is checked, not semantic correctness, actual execution,
current product revisions, or permission. The coordinator must observe checks,
verify revisions and authorization, and stop external work before invalidating it.
History and current state are committed together by atomic state.json replacement.
Disjoint tasks may run concurrently; shared services and resource conflicts remain
the host coordinator's responsibility.
Do not edit workspace files concurrently. A leftover .control.lock requires human
inspection of the previous writer before removal; it is never cleared automatically.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

import loop_workspace as workspace_api
from loop_workspace import require, nonempty


def validate_extra(workspace, plan, state):
    """Validate companion metadata, including retained immutable evidence."""
    history = state.get('history', [])
    require(isinstance(history, list), 'history must be an array')
    for event in history:
        require(isinstance(event, dict) and nonempty(event.get('action'))
                and nonempty(event.get('timestamp')), 'invalid transition history')
        previous_tasks = workspace_api.mapping(event.get('previous_tasks', {}), 'history previous_tasks')
        workspace_api.mapping(event.get('previous_decisions', {}), 'history previous_decisions')
        for name, previous in previous_tasks.items():
            require(nonempty(name) and isinstance(previous, dict), 'invalid task history')
            for record in workspace_api.array(previous.get('evidence', []), 'historical evidence'):
                workspace_api.mapping(record, 'historical evidence record')
                require(nonempty(record.get('check_id')), 'historical check ID must be nonempty')
                # Replanning can remove tasks/checks; their archived logs remain immutable.
                workspace_api.validate_evidence(workspace, previous, record, {record['check_id']})
    for item in state['tasks'].values():
        if item['status'] == 'running':
            require(nonempty(item.get('running_revision')),
                    'running task needs running_revision; reconcile legacy running state first')
            require(all(record['artifact_version'] == item['running_revision']
                        for record in item['evidence']), 'running evidence revision mismatch')
        require(len({record['check_id'] for record in item['evidence']}) == len(item['evidence']),
                'duplicate current check records')


def descendants(plan, name):
    affected = {name}
    while True:
        more = {task['id'] for task in plan['tasks'] if set(task['depends_on']) & affected}
        if more <= affected:
            return affected
        affected |= more


def used_paths(state):
    paths = {workspace_api.scope_path(record['path']) for task in state['tasks'].values()
             for record in task['evidence']}
    for event in state.get('history', []):
        for task in event.get('previous_tasks', {}).values():
            paths.update(workspace_api.scope_path(record['path']) for record in task.get('evidence', []))
    return paths


def transition(workspace, plan, state, args):
    previous = copy.deepcopy(state)
    event = {'action': args.command, 'timestamp': datetime.now(timezone.utc).isoformat(),
             'previous_tasks': {}, 'previous_decisions': {}}
    tasks = {task['id']: task for task in plan['tasks']}
    if args.command in {'todo-add', 'todo-set'}:
        todos = state.setdefault('todos', [])
        found = [todo for todo in todos if todo['id'] == args.todo]
        if args.command == 'todo-add':
            require(not found, 'todo already exists')
            require(workspace_api.nonempty(args.todo) and nonempty(args.title), 'todo id and title are required')
            require(args.task in tasks, 'unknown task')
            todo = {'id': args.todo, 'title': args.title, 'task_id': args.task,
                    'requirement_id': args.requirement, 'status': 'pending'}
            todos.append(todo)
        else:
            require(found, 'unknown todo')
            todo = found[0]
            task_status = state['tasks'][todo['task_id']]['status']
            # Progress belongs to work under way; a todo never marks its task verified.
            require(args.status in {'pending', 'dropped'} or task_status in {'running', 'passed'},
                    'start the todo\'s task before progressing it')
            require(args.status != 'dropped' or nonempty(args.reason), 'dropping a todo needs a reason')
            event['previous_todo'] = copy.deepcopy(todo)
            todo['status'] = args.status
            todo.pop('reason', None)
            if args.reason:
                todo['reason'] = args.reason
        event['todo'] = copy.deepcopy(todo)
    elif args.command == 'resolve-decision':
        require(args.decision in state['decisions'], 'unknown decision')
        item = state['decisions'][args.decision]
        require(item['status'] == 'pending', 'resolved decision requires coordinator reconciliation')
        require(nonempty(args.answer) and nonempty(args.source), 'actual answer and source are required')
        event['previous_decisions'][args.decision] = copy.deepcopy(item)
        item.update(status='resolved', answer=args.answer, source=args.source,
                    outcome=args.outcome, artifact_version=args.revision)
        event['decision'] = args.decision
        event['resolution'] = copy.deepcopy(item)
    else:
        require(args.task in tasks, 'unknown task')
        item = state['tasks'][args.task]
        event['task'] = args.task
        affected = {args.task}
        if args.command == 'start':
            require(nonempty(args.revision), 'revision must be nonempty')
            readiness = workspace_api.status(plan, state, [])
            require(args.task in readiness['ready'], 'task is not ready (state, dependency, decision, or attempt limit)')
            _, _, warnings = workspace_api.validate_plan(plan)
            conflicts = [warning for warning in warnings if args.task in warning['tasks']
                         and any(name in readiness['running'] for name in warning['tasks'])]
            require(not conflicts, 'task scopes overlap running work; serialize conflicting tasks')
            item.update(status='running', attempts=item['attempts'] + 1,
                        running_revision=args.revision, verified_revision=None, evidence=[])
            item.pop('block_reason', None)
        elif args.command == 'set-revision':
            require(item['status'] == 'running', 'task must be running')
            require(not item['evidence'], 'cannot change revision after recording checks; finish failed before retrying')
            require(nonempty(args.revision) and nonempty(args.reason), 'revision and change reason must be nonempty')
            item['running_revision'] = args.revision
            event['reason'] = args.reason
            event['revision'] = args.revision
        elif args.command in {'record-check', 'finish'}:
            require(item['status'] == 'running', 'task must be running')
            require(nonempty(args.revision) and args.revision == item.get('running_revision'),
                    'revision must match the running attempt')
            require(all(state['tasks'][dep]['status'] == 'passed' for dep in tasks[args.task]['depends_on'])
                    and all(workspace_api.decision_satisfied(state['decisions'][dep])
                            for dep in tasks[args.task]['decision_ids']), 'task gates are no longer satisfied')
            if args.command == 'record-check':
                checks = {check['id'] for check in tasks[args.task]['checks']}
                require(args.check in checks, 'unknown check')
                require(not any(record['check_id'] == args.check for record in item['evidence']),
                        'check already recorded this attempt; finish failed before retrying')
                path = workspace_api.scope_path(args.path)
                require(path not in used_paths(state), 'evidence path was already used; never overwrite/reuse logs')
                record = {'check_id': args.check, 'result': args.result, 'path': path,
                          'artifact_version': args.revision}
                # Validate containment and every symlink component before reading bytes.
                parts = Path(path).parts
                require(len(parts) > 1 and parts[0] == 'evidence', 'evidence must be strictly inside evidence/')
                target = workspace
                for part in parts:
                    target = target / part
                    require(not target.is_symlink(), 'symlink evidence component: ' + str(target))
                record['sha256'] = workspace_api.digest(workspace_api.regular_file(target))
                workspace_api.validate_evidence(workspace, item, record, checks)
                item['evidence'].append(record)
                event['record'] = copy.deepcopy(record)
            else:
                require(nonempty(args.reason), 'finish needs an observed result or failure reason')
                item.update(status=args.result, verified_revision=args.revision if args.result == 'passed' else None)
                item.pop('running_revision', None)
                event['reason'] = args.reason
                # The shared validator enforces all required checks and matching revisions for pass.
        else:
            require(nonempty(args.reason), 'a concrete reason is required')
            require(item['status'] != 'cancelled', 'cancelled tasks require coordinator reconciliation')
            affected = descendants(plan, args.task)
            for name in affected:
                target = state['tasks'][name]
                if target['status'] == 'cancelled':
                    continue
                target.update(status='stale', verified_revision=None)
                target.pop('running_revision', None)
                target.pop('block_reason', None)
            if args.command in {'block', 'cancel'}:
                item['status'] = 'blocked' if args.command == 'block' else 'cancelled'
                item['block_reason'] = args.reason
            event['reason'] = args.reason
        event['previous_tasks'] = {name: previous['tasks'][name] for name in sorted(affected)}
    state.setdefault('history', []).append(event)
    return event


def apply(args):
    workspace, _, _, _, _ = workspace_api.load_workspace(args.workspace)
    lock = workspace / '.control.lock'
    # Cooperating writers fail closed instead of racing or stealing an existing lock.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()) + '\n')
        workspace, files, plan, state, _ = workspace_api.load_workspace(workspace)
        validate_extra(workspace, plan, state)
        event = transition(workspace, plan, state, args)
        workspace_api.load_workspace(workspace, state_override=state)
        validate_extra(workspace, plan, state)
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix='.state-', dir=workspace)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(workspace_api.encode(state))
                stream.flush()
                os.fsync(stream.fileno())
            require(all(workspace_api.regular_file(workspace / name) == data
                        for name, data in files.items()), 'workspace changed during transition; refusing overwrite')
            os.replace(temporary, workspace / 'state.json')
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)
        return {'action': event['action'], 'verification_scope': workspace_api.SCOPE,
                'state': str(workspace / 'state.json')}
    finally:
        lock.unlink()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start', help='start ready task and consume one attempt; never runs it')
    revision = commands.add_parser('set-revision', help='record actual post-work revision of running task before any check is recorded')
    record = commands.add_parser('record-check', help='register one existing nonempty actual log, never write or execute it')
    finish = commands.add_parser('finish', help='finish running task; pass requires every current check passed at this revision')
    decision = commands.add_parser('resolve-decision', help='record actual answer and source; never infer or grant permission')
    todo_add = commands.add_parser('todo-add', help='add a requirement todo under a plan task; status starts pending')
    todo_set = commands.add_parser('todo-set', help='move a todo to pending, in_progress, completed or dropped; never passes its task')
    mutation = [commands.add_parser(name, help=description) for name, description in [
        ('invalidate', 'mark task and descendants stale without resetting attempts or deleting evidence'),
        ('block', 'block task and invalidate descendants; record why'),
        ('cancel', 'cancel task and invalidate descendants; does not stop external processes')]]
    for command in [start, revision, record, finish, decision, todo_add, todo_set, *mutation]:
        command.add_argument('--workspace', required=True, help='existing .agent-loop/<run-id>')
    for command in [start, revision, record, finish, *mutation]:
        command.add_argument('--task', required=True, help='exact plan task ID')
    for command in [start, revision, record, finish]:
        command.add_argument('--revision', required=True, help='actual artifact/input/environment revision, including dirty changes')
    for command in [revision, finish, *mutation]:
        command.add_argument('--reason', required=True, help='actual result, failure, change, blocker, or cancellation reason')
    record.add_argument('--check', required=True, help='exact required check ID')
    record.add_argument('--path', required=True, help='new unused existing log path relative to workspace, strictly under evidence/')
    record.add_argument('--result', required=True, choices=['passed', 'failed', 'not_run'])
    finish.add_argument('--result', required=True, choices=['passed', 'failed'])
    for command in [todo_add, todo_set]:
        command.add_argument('--todo', required=True, help='todo ID, unique in the run')
    todo_add.add_argument('--title', required=True, help='one concrete, checkable step')
    todo_add.add_argument('--task', required=True, help='plan task this todo belongs to')
    todo_add.add_argument('--requirement', help='plan requirement ID this todo serves')
    todo_set.add_argument('--status', required=True, choices=['pending', 'in_progress', 'completed', 'dropped'])
    todo_set.add_argument('--reason', help='required for dropped; optional note otherwise')
    decision.add_argument('--decision', required=True, help='exact pending decision ID')
    decision.add_argument('--answer', required=True, help='actual explicit answer, not a placeholder')
    decision.add_argument('--source', required=True, help='actual message ID, permalink, or other traceable source')
    decision.add_argument('--outcome', required=True, choices=['answered', 'approved', 'rejected', 'revision_requested'])
    decision.add_argument('--revision', help='reviewed artifact version; required when plan pins artifact_version')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        print(json.dumps(apply(args), ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
