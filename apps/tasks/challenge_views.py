"""
Challenge views — global, open-to-all coding challenges with coin rewards.

Add these to your existing apps/tasks/views.py, or import them from here
by adding to urls.py:  from apps.tasks.challenge_views import ...
"""
import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.tasks.models import Task
from apps.submissions.models import Submission, SolvedChallenge
from apps.users.models import CoinTransaction

logger = logging.getLogger(__name__)

# ── Challenge list ────────────────────────────────────────────────────────────

@login_required
def challenge_list(request):
    """
    Public list of all published global challenges.
    Supports filtering by difficulty.
    """
    qs = (
        Task.objects
        .filter(scope=Task.SCOPE_GLOBAL, status=Task.STATUS_PUBLISHED)
        .annotate(solve_count=Count('solved_challenges', distinct=True))
        .order_by('difficulty', '-created_at')
    )

    difficulty = request.GET.get('difficulty', '').strip()
    if difficulty in (Task.DIFF_EASY, Task.DIFF_MEDIUM, Task.DIFF_HARD):
        qs = qs.filter(difficulty=difficulty)

    # IDs the current user has already solved — used for ✓ badges in the list
    solved_ids = set(
        SolvedChallenge.objects
        .filter(user=request.user)
        .values_list('task_id', flat=True)
    )

    paginator  = Paginator(qs, 20)
    page_obj   = paginator.get_page(request.GET.get('page'))

    return render(request, 'challenges/challenge_list.html', {
        'page_obj':        page_obj,
        'solved_ids':      solved_ids,
        'difficulty':      difficulty,
        'total_published': Task.objects.filter(
            scope=Task.SCOPE_GLOBAL, status=Task.STATUS_PUBLISHED
        ).count(),
    })


# ── Challenge detail ──────────────────────────────────────────────────────────

@login_required
def challenge_detail(request, pk):
    """
    Show problem statement + code editor for a published global challenge.
    """
    task = get_object_or_404(
        Task, pk=pk, scope=Task.SCOPE_GLOBAL, status=Task.STATUS_PUBLISHED,
    )
    solve_record = SolvedChallenge.objects.filter(
        user=request.user, task=task,
    ).select_related('submission').first()

    # The user's previous submissions for this task (latest 10)
    prev_submissions = (
        Submission.objects
        .filter(student=request.user, task=task, session__isnull=True)
        .order_by('-created_at')[:10]
    )

    return render(request, 'challenges/challenge_detail.html', {
        'task':             task,
        'solve_record':     solve_record,
        'prev_submissions': prev_submissions,
        'languages':        Submission.LANG_CHOICES,
    })


# ── Run against example cases (fast feedback, no coin award) ─────────────────

@login_required
@require_POST
def challenge_run(request, pk):
    """
    Run submitted code against example (visible) test cases only.
    Returns JSON — no Submission object is created.
    """
    task     = get_object_or_404(Task, pk=pk, scope=Task.SCOPE_GLOBAL, status=Task.STATUS_PUBLISHED)
    code     = request.POST.get('code', '').strip()
    language = request.POST.get('language', Submission.LANG_PYTHON)

    if not code:
        return JsonResponse({'error': 'No code provided.'}, status=400)
    if language not in dict(Submission.LANG_CHOICES):
        return JsonResponse({'error': 'Unsupported language.'}, status=400)

    example_cases = list(task.example_cases)
    if not example_cases:
        return JsonResponse({'error': 'No example test cases for this task.'}, status=400)

    from apps.runner.services import run_code_sync
    results = run_code_sync(
        code, example_cases,
        task.time_limit, task.memory_limit,
        language=language,
    )
    return JsonResponse({'results': results})


# ── Submit against hidden cases (creates Submission, may award coins) ─────────

@login_required
@require_POST
def challenge_submit(request, pk):
    """
    Full submission against hidden test cases.
    Runs synchronously (same as session submissions) — no Celery needed.
    Returns the full result immediately so the frontend needs no polling.
    """
    from django.conf import settings as django_settings
    task     = get_object_or_404(Task, pk=pk, scope=Task.SCOPE_GLOBAL, status=Task.STATUS_PUBLISHED)
    code     = request.POST.get('code', '').strip()
    language = request.POST.get('language', Submission.LANG_PYTHON)

    if not code:
        return JsonResponse({'error': 'No code provided.'}, status=400)
    if language not in dict(Submission.LANG_CHOICES):
        return JsonResponse({'error': 'Unsupported language.'}, status=400)
    if len(code.encode()) > getattr(django_settings, 'MAX_CODE_SIZE', 65536):
        return JsonResponse({'error': 'Code exceeds maximum allowed size.'}, status=400)

    sub = Submission.objects.create(
        student  = request.user,
        task     = task,
        session  = None,   # marks this as a global (non-session) submission
        code     = code,
        language = language,
        status   = Submission.STATUS_PENDING,
    )

    # Run synchronously — same approach as session submissions
    from apps.runner.services import _evaluate_submission_sync
    _evaluate_submission_sync(sub.pk)

    # Reload from DB to get the saved results
    sub.refresh_from_db()

    coins_earned = None
    if sub.is_correct:
        solve = SolvedChallenge.objects.filter(
            user=request.user, task=task, submission=sub,
        ).first()
        if solve:
            coins_earned = solve.coins_awarded

    return JsonResponse({
        'submission_id': sub.pk,
        'status':        sub.status,
        'is_correct':    sub.is_correct,
        'passed':        sub.passed_count,
        'total':         sub.total_count,
        'coins_earned':  coins_earned,
        'results':       sub.results,
    })


# ── Global leaderboard ────────────────────────────────────────────────────────

@login_required
def leaderboard(request):
    """
    Global leaderboard ranked by total coins earned.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Top 100 users by total coins
    rankings = (
        User.objects
        .annotate(
            total_coins  = Sum('coin_transactions__amount'),
            solved_count = Count('solved_challenges', distinct=True),
        )
        .filter(total_coins__gt=0)
        .order_by('-total_coins', '-solved_count')[:100]
    )

    # Current user's rank (simple count of users with more coins)
    my_balance = request.user.coin_balance
    my_rank    = None
    if my_balance > 0:
        my_rank = (
            User.objects
            .annotate(total_coins=Sum('coin_transactions__amount'))
            .filter(total_coins__gt=my_balance)
            .count()
        ) + 1

    return render(request, 'challenges/leaderboard.html', {
        'rankings':    rankings,
        'my_rank':     my_rank,
        'my_balance':  my_balance,
    })