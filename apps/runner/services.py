"""
Runner services — multi-language code execution.

Supported languages: Python, JavaScript (Node.js), C++, C
"""
import logging
import os
import subprocess
import tempfile
import time
from typing import List

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Language configs ──────────────────────────────────────────────────────────

LANG_CONFIG = {
    'python': {
        'filename': 'solution.py',
        'compile': None,
        'run': ['python3', '{file}'],
    },
    'javascript': {
        'filename': 'solution.js',
        'compile': None,
        'run': ['node', '{file}'],
    },
    'cpp': {
        'filename': 'solution.cpp',
        'compile': ['g++', '-O2', '-o', '{exe}', '{file}'],
        'run': ['{exe}'],
    },
    'c': {
        'filename': 'solution.c',
        'compile': ['gcc', '-O2', '-o', '{exe}', '{file}'],
        'run': ['{exe}'],
    },
}


# ── Public API ────────────────────────────────────────────────────────────────

def run_code_sync(code: str, test_cases, time_limit: int, memory_limit: str,
                  language: str = 'python') -> List[dict]:
    """
    Run `code` in `language` against each TestCase.
    Returns list of result dicts.
    """
    results = []
    for tc in test_cases:
        result = _run_single(code, tc.input_data, time_limit, language)
        passed = (
            result['exit_code'] == 0
            and result['stdout'].strip() == tc.expected_output.strip()
        )
        results.append({
            'test_case_id': tc.pk,
            'input':    tc.input_data    if tc.is_example else '(hidden)',
            'expected': tc.expected_output if tc.is_example else '(hidden)',
            'stdout':   result['stdout'],
            'stderr':   result['stderr'],
            'exit_code': result['exit_code'],
            'time_used': result['time_used'],
            'passed':   passed,
            'error':    result.get('error'),
        })
    return results


def _run_single(code: str, stdin_data: str, time_limit: int,
                language: str = 'python') -> dict:
    return _run_in_subprocess(code, stdin_data, time_limit, language)


# ── Subprocess runner (multi-language) ───────────────────────────────────────

def _run_in_subprocess(code: str, stdin_data: str, time_limit: int,
                       language: str = 'python') -> dict:
    cfg = LANG_CONFIG.get(language, LANG_CONFIG['python'])

    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, cfg['filename'])
        exe_path = os.path.join(tmpdir, 'solution')

        with open(src_path, 'w') as f:
            f.write(code)

        # ── Compile (C / C++) ──
        if cfg['compile']:
            compile_cmd = [
                c.replace('{file}', src_path).replace('{exe}', exe_path)
                for c in cfg['compile']
            ]
            try:
                comp = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    timeout=15,
                )
                if comp.returncode != 0:
                    return {
                        'stdout': '',
                        'stderr': comp.stderr.decode(errors='replace'),
                        'exit_code': comp.returncode,
                        'time_used': 0,
                        'error': 'Compilation error',
                    }
            except subprocess.TimeoutExpired:
                return {
                    'stdout': '', 'stderr': 'Compilation timed out',
                    'exit_code': -1, 'time_used': 0, 'error': 'CE',
                }
            except FileNotFoundError:
                return {
                    'stdout': '',
                    'stderr': f'Compiler not found for {language}. Please use Python or JavaScript.',
                    'exit_code': -1, 'time_used': 0, 'error': 'No compiler',
                }

        # ── Run ──
        run_cmd = [
            c.replace('{file}', src_path).replace('{exe}', exe_path)
            for c in cfg['run']
        ]

        start = time.monotonic()
        try:
            proc = subprocess.run(
                run_cmd,
                input=stdin_data.encode(),
                capture_output=True,
                timeout=time_limit,
            )
            elapsed = time.monotonic() - start
            return {
                'stdout':   proc.stdout.decode(errors='replace'),
                'stderr':   proc.stderr.decode(errors='replace'),
                'exit_code': proc.returncode,
                'time_used': round(elapsed, 3),
                'error':    None,
            }
        except subprocess.TimeoutExpired:
            return {
                'stdout': '', 'stderr': f'Time limit exceeded ({time_limit}s)',
                'exit_code': -1, 'time_used': time_limit, 'error': 'TLE',
            }
        except FileNotFoundError:
            return {
                'stdout': '',
                'stderr': f'Runtime not found for {language}. Please use Python.',
                'exit_code': -1, 'time_used': 0, 'error': 'No runtime',
            }
        except Exception as exc:
            logger.exception('Runner error')
            return {
                'stdout': '', 'stderr': str(exc),
                'exit_code': -1, 'time_used': 0, 'error': str(exc),
            }


# ── Sync evaluator (called directly — no Celery) ─────────────────────────────

def _evaluate_submission_sync(submission_pk: int):
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
        # Fall back to all test cases if no hidden ones
        hidden_cases = list(sub.task.test_cases.all())
    if not hidden_cases:
        sub.status = Submission.STATUS_ERROR
        sub.results = [{'error': 'No test cases configured for this task'}]
        sub.save()
        return

    results = run_code_sync(
        sub.code, hidden_cases,
        sub.task.time_limit, sub.task.memory_limit,
        language=sub.language,
    )
    is_correct = all(r['passed'] for r in results)

    sub.is_correct   = is_correct
    sub.status       = Submission.STATUS_PASSED if is_correct else Submission.STATUS_FAILED
    sub.results      = results
    sub.evaluated_at = timezone.now()
    sub.save()

    logger.info('Submission %s [%s] → %s', submission_pk, sub.language, sub.status)

    if sub.session_id:
        _broadcast_session_event(sub.session_id, 'submission_result', {
            'student':       sub.student.username,
            'student_id':    sub.student.pk,
            'submission_id': sub.pk,
            'status':        sub.status,
            'is_correct':    sub.is_correct,
        })
