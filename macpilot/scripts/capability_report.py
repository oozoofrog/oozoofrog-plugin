"""Trusted capability inventory and fail-closed report lifecycle; no UI or model work."""
from contextlib import contextmanager
import json
import os
from pathlib import Path

FULL_CHECKS = (('wait', 'disabled'),
 ('wait', 'delayed_enabled'),
 ('wait', 'replaced_node'),
 ('wait', 'poll_without_notification'),
 ('wait', 'focused'),
 ('wait', 'disappeared'),
 ('wait', 'appeared'),
 ('wait', 'geometry_settled'),
 ('wait', 'timeout_is_not_success'),
 ('wait', 'partial_cannot_prove_absence'),
 ('wait', 'duplicate_rejected'),
 ('outcome', 'noop_unverified'),
 ('outcome', 'value_postcondition_scoped'),
 ('trace', 'default_disabled'),
 ('trace', 'before_after_no_text'),
 ('trace', 'secure_values_omitted'),
 ('trace', 'before_frame_integrity'),
 ('trace', 'after_frame_integrity'),
 ('trace', 'html_export'),
 ('trace', 'bounded_retention'),
 ('trace', 'failed_trace_does_not_repeat_action'),
 ('workflow', 'parameterized_recipe'),
 ('workflow', 'same_run_not_replayed'),
 ('workflow', 'run_mismatch_rejected'),
 ('workflow', 'late_invalid_no_mutation'),
 ('workflow', 'failed_postcondition_stops'),
 ('workflow', 'durable_receipt'),
 ('workflow', 'cancellation_receipt'),
 ('interrupt', 'foreign_event_stops_and_releases'),
 ('interrupt', 'task_interrupted'),
 ('interrupt', 'blocked_until_explicit_resume'),
 ('interrupt', 'resume_invalidates_old_observation'),
 ('interrupt', 'owned_events_do_not_self_interrupt'),
 ('image', 'disabled_by_default'),
 ('image', 'visionkit_transcript_reaches_hybrid_ranker'),
 ('image', 'real_model_locates_folder'),
 ('image', 'template_retrieval'),
 ('image', 'explicit_region_scope'),
 ('image', 'oversized_template_rejected'),
 ('image', 'vector_cache_reused'),
 ('image', 'second_query_reuses_candidates'),
 ('image', 'absent_object_abstention'),
 ('image', 'threshold_abstention'),
 ('image', 'duplicate_locations_abstain'),
 ('image', 'changed_pixels_invalidate'))


def required_checks(stage):
    if stage == 'all': return FULL_CHECKS
    if stage == 'image': return tuple(item for item in FULL_CHECKS if item[0] == 'image')
    raise ValueError('Unknown capability stage')


def validate_report(report, required_stage='all'):
    if (report.get('schema') != 'macpilot-capability-check/2'
            or report.get('stage') != required_stage or report.get('suiteStatus') != 'passed'
            or report.get('completed') is not True or report.get('bodyError') or report.get('cleanupError')):
        raise ValueError('Feature suite completion or stage is not valid')
    checks = report.get('checks')
    if not isinstance(checks, list) or not all(isinstance(item, dict) for item in checks):
        raise ValueError('Feature check inventory is not valid')
    if any(not isinstance(item.get(key), str) or not item[key] for item in checks for key in ('feature', 'id')):
        raise ValueError('Feature check identity is not valid')
    identities = [(item.get('feature'), item.get('id')) for item in checks]
    expected = required_checks(required_stage)
    if len(identities) != len(expected) or len(set(identities)) != len(identities) or set(identities) != set(expected):
        raise ValueError('Feature check inventory is missing, duplicated, or unexpected')
    if any(item.get('status') != 'PASS' for item in checks):
        raise ValueError('Feature runtime checks did not all pass')


class CapabilityReport:
    def __init__(self, path, stage, binary_sha256, checks):
        self.path = Path(path)
        self.data = dict(schema='macpilot-capability-check/2', stage=stage, suiteStatus='incomplete',
                         completed=False, checks=checks, physicalInput='NOT_RUN', binarySHA256=binary_sha256)
        self.checkpoint()

    def checkpoint(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + '\n')
        temporary.chmod(0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def error_metadata(error):
        # Never copy exception arguments, input text, paths, or tracebacks into completion metadata.
        return dict(type=type(error).__name__)

    @contextmanager
    def run(self, cleanup):
        body_error = None
        cleanup_error = None
        self.data.update(suiteStatus='incomplete', completed=False)
        self.data.pop('bodyError', None)
        self.data.pop('cleanupError', None)
        self.checkpoint()
        try:
            yield
        except BaseException as error:
            body_error = error
            self.data['bodyError'] = self.error_metadata(error)
            raise
        finally:
            try:
                cleanup()
            except BaseException as error:
                cleanup_error = error
                self.data['cleanupError'] = self.error_metadata(error)
            if body_error is not None or cleanup_error is not None:
                self.data.update(suiteStatus='failed', completed=False)
            else:
                candidate = dict(self.data, suiteStatus='passed', completed=True)
                try:
                    validate_report(candidate, self.data['stage'])
                except ValueError:
                    self.data.update(suiteStatus='incomplete', completed=False)
                else:
                    self.data.update(suiteStatus='passed', completed=True)
            self.checkpoint()
            if body_error is None and cleanup_error is not None:
                raise cleanup_error
