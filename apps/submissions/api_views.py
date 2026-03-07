"""
JSON API endpoints consumed by the browser code editor.

POST /api/run/   – run code against example test cases (fast, not queued)
POST /api/submit/ – queue final submission against hidden tests
GET  /api/status/<id>/ – poll submission status
GET  /api/leaderboard/<session_pk>/ – poll leaderboard data
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings

from apps.tasks.models import Task, TestCase
from apps.sessions_app.models import Session
from apps.sessions_app.views import _broadcast_session_event
from .models import Submission
from apps.runner.services import run_code_sync, evaluate_submission_async

logger = logging.getLogger(__name__)


def _check_rate_limit(request, key_prefix, limit):
    """Simple in-memory rate limiter using Django cache."""
    from django.core.cache import cache
    cache_key = f'rate_{key_prefix}_{request.user.pk}'
    count = cache.get(cache_key, 0)
    if count >= limit:
        return False
    cache.set(cache_key, count + 1, timeout=60)
    return True


@login_required
@require_POST
def run_code(request):
    """
    Run student code against EXAMPLE test cases synchronously.
    Always returns results immediately — no queue, no polling.
    """
    if not request.user.is_student:
        return JsonResponse({'error': 'Students only'}, status=403)

    if not _check_rate_limit(request, 'run', settings.RUN_RATE_LIMIT):
        return JsonResponse({'error': 'Rate limit exceeded. Please wait a moment.'}, status=429)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    task_pk = body.get('task_id')
    session_pk = body.get('session_id')
    code = body.get('code', '')

    if not code.strip():
        return JsonResponse({'error': 'Code cannot be empty'}, status=400)
    if len(code.encode()) > settings.MAX_CODE_SIZE:
        return JsonResponse({'error': 'Code exceeds size limit (64 KB)'}, status=400)

    task = get_object_or_404(Task, pk=task_pk)
    session = get_object_or_404(Session, pk=session_pk)

    if not session.can_student_participate(request.user):
        return JsonResponse({'error': 'Session not active or you are not enrolled'}, status=403)

    example_cases = list(task.example_cases)
    if not example_cases:
        # No example cases — run against an empty test so student still gets feedback
        from apps.tasks.models import TestCase as TC
        class EmptyCase:
            pk = 0
            input_data = task.example_input or ''
            expected_output = task.example_output or ''
            is_example = True
        example_cases = [EmptyCase()]

    results = run_code_sync(code, example_cases, task.time_limit, task.memory_limit)

    _broadcast_session_event(session.pk, 'ran_example', {
        'student': request.user.username,
        'student_id': request.user.pk,
    })

    return JsonResponse({'results': results, 'sync': True})


@login_required
@require_POST
def submit_code(request):
    """
    Queue a final submission to be evaluated against hidden test cases.
    Returns submission ID for polling.
    """
    if not request.user.is_student:
        return JsonResponse({'error': 'Students only'}, status=403)

    if not _check_rate_limit(request, 'submit', settings.SUBMIT_RATE_LIMIT):
        return JsonResponse({'error': 'Rate limit exceeded. Please wait a moment.'}, status=429)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    task_pk = body.get('task_id')
    session_pk = body.get('session_id')
    code = body.get('code', '')

    if not code.strip():
        return JsonResponse({'error': 'Code cannot be empty'}, status=400)
    if len(code.encode()) > settings.MAX_CODE_SIZE:
        return JsonResponse({'error': 'Code exceeds size limit (64 KB)'}, status=400)

    task = get_object_or_404(Task, pk=task_pk)
    session = get_object_or_404(Session, pk=session_pk)

    if not session.can_student_participate(request.user):
        return JsonResponse({'error': 'Session not active'}, status=403)

    # Create submission record
    submission = Submission.objects.create(
        student=request.user,
        task=task,
        session=session,
        code=code,
        status=Submission.STATUS_PENDING,
    )

    # Broadcast to teacher
    _broadcast_session_event(session.pk, 'submitted', {
        'student': request.user.username,
        'student_id': request.user.pk,
        'submission_id': submission.pk,
    })

    # In dev mode (no Celery), evaluate synchronously right here and
    # return the full result so the browser doesn't need to poll.
    use_celery = _try_celery(submission.pk)
    if not use_celery:
        submission.refresh_from_db()
        return JsonResponse({
            'submission_id': submission.pk,
            'status': submission.status,
            'is_correct': submission.is_correct,
            'results': submission.results,
            'passed_count': submission.passed_count,
            'total_count': submission.total_count,
            'sync': True,   # tells the browser to skip polling
        })

    return JsonResponse({'submission_id': submission.pk, 'status': submission.status, 'sync': False})


def _try_celery(submission_pk: int) -> bool:
    """
    In DEBUG mode: always run synchronously (no Celery needed).
    In production: queue via Celery; fall back to sync if unavailable.
    Returns True if queued async, False if ran synchronously.
    """
    from django.conf import settings
    from apps.runner.services import _evaluate_submission_sync

    if settings.DEBUG:
        # Dev mode: just run right now, no queue needed
        _evaluate_submission_sync(submission_pk)
        return False

    try:
        from apps.runner.tasks import evaluate_submission_task
        evaluate_submission_task.delay(submission_pk)
        return True
    except Exception:
        _evaluate_submission_sync(submission_pk)
        return False


@login_required
def submission_status(request, pk):
    """Poll endpoint for submission evaluation progress."""
    sub = get_object_or_404(Submission, pk=pk, student=request.user)
    return JsonResponse({
        'status': sub.status,
        'is_correct': sub.is_correct,
        'results': sub.results,
        'passed_count': sub.passed_count,
        'total_count': sub.total_count,
    })


@login_required
def leaderboard_data(request, session_pk):
    """JSON leaderboard for a session, used by live polling."""
    session = get_object_or_404(Session, pk=session_pk)
    students = session.group.students.all()
    board = []
    for student in students:
        subs = Submission.objects.filter(student=student, session=session).order_by('created_at')
        best = subs.filter(is_correct=True).first()
        board.append({
            'username': student.get_full_name() or student.username,
            'attempts': subs.count(),
            'passed': best is not None,
            'submitted_at': best.created_at.isoformat() if best else None,
        })
    board.sort(key=lambda x: (not x['passed'], x['submitted_at'] or '9999'))
    return JsonResponse({'board': board})
