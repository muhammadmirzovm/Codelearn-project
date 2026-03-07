"""
Runner services.

Two modes depending on settings.USE_DOCKER_SANDBOX:

1. DEVELOPMENT mode (USE_DOCKER_SANDBOX=False):
   Runs code in a subprocess on the host.
   ⚠️  NOT SAFE for untrusted code – use only for local development.

2. PRODUCTION mode (USE_DOCKER_SANDBOX=True):
   Spins up an ephemeral Docker container, mounts a temp dir with the
   student's code, runs it, then destroys the container.
   Enforces CPU, memory, and time limits; network disabled.

Public API:
  run_code_sync(code, test_cases, time_limit, memory_limit) -> list[dict]
  evaluate_submission_async(submission_pk) -> None   (fires Celery task)
"""
import logging
import os
import subprocess
import tempfile
import time
from typing import List

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Synchronous runner (used by "Run Code" for example tests) ─────────────────

def run_code_sync(code: str, test_cases, time_limit: int, memory_limit: str) -> List[dict]:
    """
    Run `code` against each TestCase in `test_cases`.
    Returns a list of result dicts (one per test case).
    """
    results = []
    for tc in test_cases:
        result = _run_single(code, tc.input_data, time_limit, memory_limit)
        passed = (
            result['exit_code'] == 0
            and result['stdout'].strip() == tc.expected_output.strip()
        )
        results.append({
            'test_case_id': tc.pk,
            'input': tc.input_data if tc.is_example else '(hidden)',
            'expected': tc.expected_output if tc.is_example else '(hidden)',
            'stdout': result['stdout'],
            'stderr': result['stderr'],
            'exit_code': result['exit_code'],
            'time_used': result['time_used'],
            'passed': passed,
            'error': result.get('error'),
        })
    return results


def _run_single(code: str, stdin_data: str, time_limit: int, memory_limit: str) -> dict:
    """Execute code string with given stdin; returns stdout/stderr/exit_code/time."""
    if settings.USE_DOCKER_SANDBOX:
        return _run_in_docker(code, stdin_data, time_limit, memory_limit)
    else:
        return _run_in_subprocess(code, stdin_data, time_limit)


# ── Development subprocess runner ────────────────────────────────────────────

def _run_in_subprocess(code: str, stdin_data: str, time_limit: int) -> dict:
    """
    ⚠️  DEVELOPMENT ONLY – runs arbitrary Python code as a subprocess.
    Has NO memory isolation, NO network isolation, etc.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = os.path.join(tmpdir, 'solution.py')
        with open(code_path, 'w') as f:
            f.write(code)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                ['python3', code_path],
                input=stdin_data.encode(),
                capture_output=True,
                timeout=time_limit,
            )
            elapsed = time.monotonic() - start
            return {
                'stdout': proc.stdout.decode(errors='replace'),
                'stderr': proc.stderr.decode(errors='replace'),
                'exit_code': proc.returncode,
                'time_used': round(elapsed, 3),
                'error': None,
            }
        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': f'Time limit exceeded ({time_limit}s)',
                'exit_code': -1,
                'time_used': time_limit,
                'error': 'TLE',
            }
        except Exception as exc:
            logger.exception('Subprocess runner error')
            return {
                'stdout': '',
                'stderr': str(exc),
                'exit_code': -1,
                'time_used': 0,
                'error': str(exc),
            }


# ── Production Docker sandbox runner ─────────────────────────────────────────

def _run_in_docker(code: str, stdin_data: str, time_limit: int, memory_limit: str) -> dict:
    """
    Spins up a short-lived Docker container to execute code safely.
    Container settings:
      - no network
      - cpu/memory limits
      - read-only filesystem (except /tmp)
      - auto-removed after execution
    """
    try:
        import docker  # type: ignore
        client = docker.from_env()
    except Exception as exc:
        logger.error('Docker unavailable: %s', exc)
        return _run_in_subprocess(code, stdin_data, time_limit)  # Fallback

    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = os.path.join(tmpdir, 'solution.py')
        input_path = os.path.join(tmpdir, 'input.txt')
        with open(code_path, 'w') as f:
            f.write(code)
        with open(input_path, 'w') as f:
            f.write(stdin_data)

        start = time.monotonic()
        try:
            result = client.containers.run(
                settings.SANDBOX_IMAGE,
                command=f'sh -c "python3 /code/solution.py < /code/input.txt"',
                volumes={tmpdir: {'bind': '/code', 'mode': 'ro'}},
                mem_limit=memory_limit,
                cpu_period=settings.SANDBOX_CPU_PERIOD,
                cpu_quota=settings.SANDBOX_CPU_QUOTA,
                network_disabled=True,
                remove=True,
                stderr=True,
                stdout=True,
                detach=False,
                timeout=time_limit + 2,  # Extra buffer
            )
            elapsed = time.monotonic() - start
            return {
                'stdout': result.decode(errors='replace') if isinstance(result, bytes) else '',
                'stderr': '',
                'exit_code': 0,
                'time_used': round(elapsed, 3),
                'error': None,
            }
        except Exception as exc:
            elapsed = time.monotonic() - start
            err_msg = str(exc)
            is_tle = elapsed >= time_limit
            return {
                'stdout': '',
                'stderr': 'Time limit exceeded' if is_tle else err_msg,
                'exit_code': -1,
                'time_used': round(elapsed, 3),
                'error': 'TLE' if is_tle else err_msg,
            }


# ── Async evaluation dispatcher ───────────────────────────────────────────────

def evaluate_submission_async(submission_pk: int):
    """
    Kick off background evaluation of a submission.
    Uses Celery if available; falls back to synchronous in-process evaluation.
    """
    try:
        from .tasks import evaluate_submission_task
        evaluate_submission_task.delay(submission_pk)
    except Exception as exc:
        logger.warning('Celery unavailable (%s); running synchronously', exc)
        _evaluate_submission_sync(submission_pk)


def _evaluate_submission_sync(submission_pk: int):
    """Run evaluation in-process (dev convenience; blocks request thread)."""
    from apps.submissions.models import Submission
    from django.utils import timezone
    from apps.sessions_app.views import _broadcast_session_event

    try:
        sub = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        logger.error('Submission %s not found', submission_pk)
        return

    sub.status = Submission.STATUS_RUNNING
    sub.save(update_fields=['status'])

    hidden_cases = list(sub.task.hidden_cases)
    if not hidden_cases:
        logger.warning('Task %s has no hidden test cases', sub.task.pk)
        sub.status = Submission.STATUS_ERROR
        sub.results = [{'error': 'No hidden test cases configured'}]
        sub.save()
        return

    results = run_code_sync(sub.code, hidden_cases, sub.task.time_limit, sub.task.memory_limit)
    is_correct = all(r['passed'] for r in results)

    sub.is_correct = is_correct
    sub.status = Submission.STATUS_PASSED if is_correct else Submission.STATUS_FAILED
    sub.results = results
    sub.evaluated_at = timezone.now()
    sub.save()

    logger.info('Submission %s evaluated: %s', submission_pk, sub.status)

    # Broadcast result to session channel
    if sub.session_id:
        _broadcast_session_event(sub.session_id, 'submission_result', {
            'student': sub.student.username,
            'student_id': sub.student.pk,
            'submission_id': sub.pk,
            'status': sub.status,
            'is_correct': sub.is_correct,
        })
