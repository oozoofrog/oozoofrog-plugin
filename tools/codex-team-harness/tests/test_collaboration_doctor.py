"""Collaboration diagnosis must distinguish saved policy from actual runtime evidence."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

if sys.version_info < (3, 11):
    raise unittest.SkipTest('Optional collaboration doctor requires Python 3.11+.')

SCRIPTS = Path(__file__).resolve().parents[1]/'payload/team-coordination/scripts'
sys.path.insert(0, str(SCRIPTS))
import collaboration_doctor as doctor


TOOLS = ('create_thread', 'send_message_to_thread', 'fork_thread', 'handoff_thread',
         'move_thread_to_project', 'automation_update')


def config(mode='approve'):
    return {'plugins': {'codex-app-tools@openai-bundled': {'mcp_servers': {'codex_app': {
        'tools': {tool: {'approval_mode': mode} for tool in TOOLS}}}}}}


def read(thread_id, items=None, **fields):
    return {'source': 'codex_app.read_thread', 'requested_thread_id': thread_id,
            'response': {'thread': {'id': thread_id, **fields}, 'turns': [
                {'id': 'turn-'+thread_id, 'items': items or []}]}}


def snapshot():
    return {'schema': 1, 'team': {'leader_id': 'leader', 'coordinator_id': 'origin',
        'members': [{'thread_id': 'leader', 'role': 'leader'},
                    {'thread_id': 'core', 'role': 'core', 'leader_id': 'leader'}],
        'delegation': {'thread_id': 'origin', 'turn_id': 'turn-origin', 'message_id': 'human'}},
        'reads': [read('origin', [{'type': 'userMessage', 'id': 'human',
                                  'content': [{'type': 'text', 'text': 'Human task delegation fixture'}]}])],
        'waits': [], 'deliveries': [], 'pending_requests': []}


class CollaborationDoctorTests(unittest.TestCase):
    def codes(self, result):
        return {finding['code'] for finding in result['findings']}

    def test_approve_is_configured_not_runtime_proof_and_needs_no_rewrite(self):
        result = doctor.diagnose(config())
        self.assertEqual('configured_runtime_unverified', result['status'])
        self.assertFalse(result['runtime_verified'])
        self.assertTrue(result['read_only'])
        self.assertFalse(any(action['kind']=='configure_tool_policy' for action in result['recovery_plan']))

    def test_specific_manifest_prompt_is_not_hidden_by_server_default(self):
        policy = {'mcpServers': {'codex_app': {'default_tools_approval_mode': 'approve',
                  'tools': {'send_message_to_thread': {'approval_mode': 'prompt'}}}}}
        result = doctor.diagnose({}, app_policy=policy)
        self.assertEqual('prompt', result['tools']['send_message_to_thread']['configured_mode'])
        self.assertIn('COLLAB_TOOL_REQUIRES_APPROVAL', self.codes(result))

    def test_explicit_deny_is_preserved_not_proposed_as_auto_fix(self):
        result = doctor.diagnose(config('deny'))
        self.assertEqual('blocked', result['status'])
        self.assertIn('EXPLICIT_POLICY_RESTRICTION', self.codes(result))
        self.assertFalse(any(action['kind']=='configure_tool_policy' for action in result['recovery_plan']))

    def test_tool_filters_are_diagnosed_without_enabling_them(self):
        value = config()
        value['plugins'][doctor.PLUGIN]['mcp_servers']['codex_app']['disabled_tools']=['fork_thread']
        result = doctor.diagnose(value)
        self.assertIn('COLLAB_TOOL_DISABLED', self.codes(result))
        self.assertEqual('blocked', result['status'])

    def test_generic_wait_flag_does_not_identify_or_retry_a_command(self):
        evidence=snapshot()
        evidence['waits']=[{'source':'codex_app.wait_threads','response':{'polls':[{
            'thread':{'id':'core','status':{'type':'active','activeFlags':['waitingOnApproval']}},
            'latestToolMarker':{'type':'fileChange','status':'completed'}}]}}]
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('APPROVAL_WAIT_UNATTRIBUTED', self.codes(result))
        self.assertNotIn('COLLAB_TOOL_REQUIRES_APPROVAL', self.codes(result))
        self.assertFalse(any(action.get('retry') for action in result['recovery_plan']))
        self.assertIn('collect_exact_pending_action', {a['kind'] for a in result['recovery_plan']})

    def test_report_exposes_unobserved_members_and_missing_project_state(self):
        result=doctor.diagnose(config(), snapshot=snapshot())
        self.assertEqual(['core','leader'],result['coverage']['unobserved_member_ids'])
        self.assertFalse(result['coverage']['project_state_supplied'])

    def test_known_pending_request_with_approve_needs_runtime_reconciliation(self):
        evidence=snapshot()
        evidence['pending_requests']=[{'source':'codex_app.read_thread','thread_id':'core',
            'tool':'send_message_to_thread','request_id':'request-1','state':'pending'}]
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('APPROVED_POLICY_PENDING_REQUEST', self.codes(result))
        self.assertFalse(any(a['kind']=='configure_tool_policy' for a in result['recovery_plan']))
        self.assertFalse(any(a.get('retry') for a in result['recovery_plan']))

    def test_mismatched_read_identity_is_rejected(self):
        evidence=snapshot();entry=read('core');entry['response']['thread']['id']='other'
        evidence['reads'].append(entry)
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('EVIDENCE_IDENTITY_MISMATCH', self.codes(result))

    def test_stale_packet_is_routed_to_current_delegation_not_new_human_approval(self):
        evidence=snapshot()
        evidence['reads'].append(read('core', preview='No destination-specific human authorization has been provided. Do not send any follow-up message.'))
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertTrue(result['delegation']['human_message_observed'])
        self.assertFalse(result['delegation']['semantic_authority_verified'])
        self.assertIn('STALE_MESSAGING_PACKET', self.codes(result))
        self.assertIn('refresh_role_packet', {a['kind'] for a in result['recovery_plan']})

    def test_missing_human_source_cannot_be_replaced_by_agent_assertion(self):
        evidence=snapshot();evidence['reads'][0]['response']['turns'][0]['items'][0]['type']='agentMessage'
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertFalse(result['delegation']['human_message_observed'])
        self.assertIn('DELEGATION_SOURCE_UNVERIFIED', self.codes(result))

    def test_member_user_input_request_is_reported_to_leader(self):
        evidence=snapshot();evidence['reads'].append(read('core', [
            {'type':'mcpToolCall','id':'question-1','tool':'request_user_input_async','status':'completed'}]))
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('MEMBER_DIRECT_USER_PROMPT', self.codes(result))
        action=next(a for a in result['recovery_plan'] if a['kind']=='route_decision_to_leader')
        self.assertEqual('leader', action['destination'])

    def test_plain_final_approval_question_is_a_candidate_for_recipient_review(self):
        for text in ('계속 진행할까요?', 'Please approve the message before I send it.'):
            with self.subTest(text=text):
                evidence=snapshot();evidence['reads'].append(read('core',[
                    {'type':'agentMessage','id':'plain-question','phase':'final_answer','text':text}]))
                result=doctor.diagnose(config(),snapshot=evidence)
                self.assertIn('POSSIBLE_MEMBER_USER_QUESTION',self.codes(result))
                self.assertNotIn('MEMBER_DIRECT_USER_PROMPT',self.codes(result))

    def test_ordinary_final_report_is_not_a_user_question(self):
        evidence=snapshot();evidence['reads'].append(read('core',[
            {'type':'agentMessage','id':'report','phase':'final_answer','text':'검증을 완료했고 승인 근거를 리더에게 전달했습니다.'}]))
        self.assertNotIn('POSSIBLE_MEMBER_USER_QUESTION',self.codes(doctor.diagnose(config(),snapshot=evidence)))

    def test_unknown_leader_and_duplicate_members_are_not_resolved_by_guessing(self):
        evidence=snapshot();evidence['team']['leader_id']='missing'
        evidence['team']['members'].append(copy.deepcopy(evidence['team']['members'][1]))
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('DECISION_ROUTE_UNVERIFIED', self.codes(result))
        self.assertIn('DUPLICATE_TEAM_ID', self.codes(result))

    def test_different_owners_with_nested_active_claims_are_blocked(self):
        state={'tasks':{'a':{'owner':'first','state':'assigned','paths':['/project']},
                        'b':{'owner':'second','state':'assigned','paths':['/project/source']}},
               'harness':{'runs':{}}}
        result=doctor.diagnose(config(), state=state)
        self.assertIn('OWNERSHIP_CONFLICT', self.codes(result))
        self.assertEqual('blocked', result['status'])

    def test_same_owner_and_accepted_claims_do_not_create_false_conflict(self):
        state={'tasks':{'a':{'owner':'first','state':'assigned','paths':['/project']},
                        'b':{'owner':'first','state':'assigned','paths':['/project/source']},
                        'c':{'owner':'other','state':'accepted','paths':['/project']}},'harness':{'runs':{}}}
        self.assertNotIn('OWNERSHIP_CONFLICT', self.codes(doctor.diagnose(config(), state=state)))

    def test_uncertain_producer_blocks_duplicate_repair(self):
        state={'tasks':{},'harness':{'runs':{'run-1':{'state':'uncertain','member':'core'}}}}
        result=doctor.diagnose(config(), state=state)
        self.assertIn('UNCERTAIN_PRODUCER', self.codes(result))
        self.assertFalse(any(a.get('retry') for a in result['recovery_plan']))

    def test_send_receipt_is_submission_not_recipient_ack(self):
        evidence=snapshot();evidence['deliveries']=[{'source':'codex_app.send_message_to_thread',
            'requested_thread_id':'core','response':{'threadId':'core'}}]
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertEqual('submitted', result['deliveries'][0]['state'])
        self.assertFalse(result['deliveries'][0]['acknowledged'])

    def test_model_capacity_failure_is_not_permission_denial(self):
        evidence=snapshot();entry=read('core')
        entry['response']['turns'][0]['error']={'message':'Selected model is at capacity. Please try a different model.'}
        evidence['reads'].append(entry)
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('MODEL_CAPACITY_UNAVAILABLE', self.codes(result))
        self.assertNotIn('COLLAB_TOOL_REQUIRES_APPROVAL', self.codes(result))

    def test_conflicting_policy_layers_require_observation_not_a_runtime_claim(self):
        value={'plugins':{doctor.PLUGIN:{'mcp_servers':{'codex_app':{'default_tools_approval_mode':'prompt'}}}}}
        policy={'mcpServers':{'codex_app':{'tools':{'send_message_to_thread':{'approval_mode':'approve'}}}}}
        result=doctor.diagnose(value, app_policy=policy)
        self.assertIn('POLICY_LAYER_CONFLICT',self.codes(result))
        self.assertFalse(result['runtime_verified'])

    def test_actual_denial_is_not_worked_around_by_changing_the_tool_policy(self):
        evidence=snapshot();evidence['reads'].append(read('core',[
            {'type':'mcpToolCall','id':'denied-1','tool':'send_message_to_thread','status':'failed',
             'error':{'message':'Permission denied by user'}}]))
        result=doctor.diagnose(config('prompt'), snapshot=evidence)
        self.assertIn('TOOL_PERMISSION_DENIED',self.codes(result))
        self.assertFalse(any(a['kind']=='configure_tool_policy' and a.get('tool')=='send_message_to_thread' for a in result['recovery_plan']))

    def test_pending_request_outside_recorded_team_does_not_receive_repair_action(self):
        evidence=snapshot();evidence['pending_requests']=[{'source':'codex_app.read_thread',
            'thread_id':'unrelated','tool':'send_message_to_thread','request_id':'other-request','state':'pending'}]
        result=doctor.diagnose(config(), snapshot=evidence)
        self.assertIn('EVIDENCE_OUTSIDE_TEAM',self.codes(result))
        self.assertFalse(any(a.get('thread_id')=='unrelated' for a in result['recovery_plan']))

    def test_cli_is_read_only_and_does_not_disclose_unrelated_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'config.toml'
            text='private_token = "fixture-do-not-print"\n'+''.join(
                '[plugins."'+doctor.PLUGIN+'".mcp_servers.codex_app.tools.'+tool+']\napproval_mode = "approve"\n' for tool in TOOLS)
            path.write_text(text);before=path.read_bytes();timestamp=path.stat().st_mtime_ns
            result=subprocess.run([sys.executable,'-I','-S','-B',str(SCRIPTS/'collaboration_doctor.py'),'--config',str(path)],capture_output=True,text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn('fixture-do-not-print', result.stdout)
            self.assertTrue(json.loads(result.stdout)['read_only'])
            self.assertEqual(before,path.read_bytes());self.assertEqual(timestamp,path.stat().st_mtime_ns)
            self.assertEqual(['config.toml'],sorted(p.name for p in root.iterdir()))

    def test_invalid_config_has_structured_failure_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'config.toml';path.write_text('[invalid\n')
            result=subprocess.run([sys.executable,'-I','-S','-B',str(SCRIPTS/'collaboration_doctor.py'),'--config',str(path)],capture_output=True,text=True)
            self.assertEqual(1,result.returncode)
            self.assertEqual('blocked',json.loads(result.stdout)['status'])
            self.assertNotIn('Traceback',result.stderr)

    def test_non_object_state_cannot_be_reported_as_checked_ownership(self):
        result=doctor.diagnose(config(), state=['not a project ledger'])
        self.assertEqual('blocked',result['status'])
        self.assertIn('INVALID_INPUT_SHAPE',self.codes(result))


if __name__=='__main__':
    unittest.main()
