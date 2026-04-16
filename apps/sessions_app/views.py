import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Session, QuizAttempt, QuizAnswer
from .forms import SessionForm
from apps.submissions.models import Submission


def teacher_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher:
            return HttpResponseForbidden('Teachers only.')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def session_list(request):
    if request.user.is_teacher:
        sessions = Session.objects.filter(
            group__teacher=request.user
        ).select_related('group', 'task', 'test_pack')
    else:
        sessions = Session.objects.filter(
            group__students=request.user
        ).select_related('group', 'task', 'test_pack')
    return render(request, 'sessions/session_list.html', {'sessions': sessions})


@teacher_required
def session_create(request):
    if request.method == 'POST':
        form = SessionForm(request.user, request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.session_type = form.cleaned_data['session_type']
            session.save()
            messages.success(request, 'Session yaratildi!')
            return redirect('sessions:session_list')
    else:
        form = SessionForm(request.user)
    return render(request, 'sessions/session_form.html', {'form': form})


@teacher_required
def session_activate(request, pk):
    session = get_object_or_404(Session, pk=pk, group__teacher=request.user)
    session.is_active    = True
    session.activated_at = timezone.now()
    session.save()

    _broadcast_session(session.pk, 'session_started', {})
    _broadcast_group(session.group.pk, 'session_started', {
        'session_pk':       session.pk,
        'title':            session.title,
        'session_type':     session.session_type,
        'group_name':       session.group.name,
        'duration_minutes': session.duration_minutes,
        'join_url':         reverse('sessions:join', args=[session.pk]),
        'leaderboard_url':  reverse('sessions:leaderboard', args=[session.pk]),
    })
    messages.success(request, 'Session boshlandi!')
    return redirect('sessions:monitor', pk=pk)


@teacher_required
def session_deactivate(request, pk):
    session = get_object_or_404(Session, pk=pk, group__teacher=request.user)
    session.is_active = False
    session.save()
    _broadcast_session(session.pk, 'session_ended', {})
    _broadcast_group(session.group.pk, 'session_ended', {'session_pk': session.pk})
    messages.success(request, 'Session yopildi.')
    return redirect('sessions:session_list')


@teacher_required
def session_monitor(request, pk):
    session = get_object_or_404(Session, pk=pk, group__teacher=request.user)
    students = session.group.students.all()
    student_data = []

    if session.is_quiz:
        for student in students:
            attempt = QuizAttempt.objects.filter(session=session, student=student).first()
            student_data.append({'student': student, 'attempt': attempt, 'submission': None})
    else:
        for student in students:
            latest = Submission.objects.filter(
                student=student, session=session
            ).order_by('-created_at').first()
            student_data.append({'student': student, 'attempt': None, 'submission': latest})

    return render(request, 'sessions/session_monitor.html', {
        'session':      session,
        'student_data': student_data,
    })


@login_required
def session_join(request, pk):
    session = get_object_or_404(Session, pk=pk)
    user    = request.user

    if not request.user.is_student:
        return HttpResponseForbidden('Students only.')

    if not session.can_student_participate(user):
        if session.is_time_up:
            messages.warning(request, 'Vaqt tugadi.')
        else:
            messages.warning(request, 'Session faol emas yoki siz bu guruhda emassiz.')
        return redirect('sessions:session_list')

    activated_at_iso = session.activated_at.isoformat() if session.activated_at else ''

    if session.is_quiz:
        test_pack = session.test_pack
        questions = test_pack.questions.prefetch_related('choices').all()
        attempt, created = QuizAttempt.objects.get_or_create(
            session=session, student=user,
            defaults={'total': test_pack.questions.count()}
        )
        if attempt.status == QuizAttempt.STATUS_FINISHED:
            return redirect('sessions:quiz_results', pk=pk)

        answered_ids = list(attempt.answers.values_list('question_id', flat=True))

        if created:
            _broadcast_session(session.pk, 'student_joined', {
                'student_id': user.pk,
                'username':   user.username,
                'full_name':  user.get_full_name() or user.username,
            })

        return render(request, 'sessions/session_join_quiz.html', {
            'session':          session,
            'test_pack':        test_pack,
            'questions':        questions,
            'attempt':          attempt,
            'answered_ids':     answered_ids,
            'activated_at_iso': activated_at_iso,
        })
    else:
        task = session.task
        my_submission = Submission.objects.filter(
            student=user, session=session
        ).order_by('-created_at').first()
        return render(request, 'sessions/session_join.html', {
            'session':          session,
            'task':             task,
            'my_submission':    my_submission,
            'activated_at_iso': activated_at_iso,
        })


@login_required
def quiz_answer(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    session = get_object_or_404(Session, pk=pk)
    user    = request.user

    if not session.is_quiz:
        return JsonResponse({'error': 'Not a quiz session'}, status=400)

    attempt = get_object_or_404(QuizAttempt, session=session, student=user)
    if attempt.status == QuizAttempt.STATUS_FINISHED:
        return JsonResponse({'error': 'Already finished'}, status=400)

    data        = json.loads(request.body)
    question_id = data.get('question_id')
    choice_id   = data.get('choice_id')

    from apps.tests_app.models import Question, Choice
    question = get_object_or_404(Question, pk=question_id, test_pack=session.test_pack)
    choice   = get_object_or_404(Choice, pk=choice_id, question=question)

    QuizAnswer.objects.update_or_create(
        attempt=attempt, question=question,
        defaults={'choice': choice, 'is_correct': choice.is_correct}
    )

    answered_count = attempt.answers.count()

    _broadcast_session(session.pk, 'question_answered', {
        'student_id':     user.pk,
        'username':       user.username,
        'answered_count': answered_count,
        'total':          session.test_pack.questions.count(),
        'question_order': question.order,
    })

    return JsonResponse({'success': True, 'answered_count': answered_count})


@login_required
def quiz_finish(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    session = get_object_or_404(Session, pk=pk)
    user    = request.user
    attempt = get_object_or_404(QuizAttempt, session=session, student=user)

    if attempt.status == QuizAttempt.STATUS_FINISHED:
        return JsonResponse({'already_finished': True})

    score = attempt.answers.filter(is_correct=True).count()
    total = session.test_pack.questions.count()

    attempt.score       = score
    attempt.total       = total
    attempt.status      = QuizAttempt.STATUS_FINISHED
    attempt.finished_at = timezone.now()
    attempt.save()

    # Award coins only if ALL correct and test_pack has coin_reward
    test_pack    = session.test_pack
    coins_earned = 0
    if score == total and total > 0 and test_pack.coin_reward > 0:
        # FIX: don't use models.F — just query directly
        already_rewarded = QuizAttempt.objects.filter(
            session__test_pack=test_pack,
            student=user,
            coins_awarded=True,
        ).exclude(pk=attempt.pk).exists()
        if not already_rewarded:
            from apps.users.models import CoinTransaction
            CoinTransaction.objects.create(
                user=user,
                amount=test_pack.coin_reward,
                tx_type=CoinTransaction.TYPE_EARN,
                note=f'Quiz 100%: {test_pack.title}',
            )
            QuizAttempt.objects.filter(pk=attempt.pk).update(coins_awarded=True)
            coins_earned = test_pack.coin_reward

    _broadcast_session(session.pk, 'student_finished', {
        'student_id':  user.pk,
        'username':    user.username,
        'score':       score,
        'total':       total,
        'time_taken':  attempt.time_taken_seconds,
    })

    return JsonResponse({
        'success':      True,
        'score':        score,
        'total':        total,
        'coins_earned': coins_earned,
    })


@login_required
def quiz_results(request, pk):
    session  = get_object_or_404(Session, pk=pk)
    user     = request.user
    attempt  = get_object_or_404(QuizAttempt, session=session, student=user)
    attempts = QuizAttempt.objects.filter(
        session=session, status=QuizAttempt.STATUS_FINISHED
    ).select_related('student').order_by('-score', 'finished_at')

    id_list = list(attempts.values_list('student_id', flat=True))
    rank = id_list.index(user.pk) + 1 if user.pk in id_list else 0

    answer_map = {a.question_id: a for a in attempt.answers.select_related('choice', 'question')}
    question_results = []
    for q in session.test_pack.questions.prefetch_related('choices').all():
        ans = answer_map.get(q.pk)
        question_results.append({
            'question':      q,
            'answer':        ans,
            'is_correct':    ans.is_correct if ans else False,
            'chosen_choice': ans.choice if ans else None,
        })

    return render(request, 'sessions/session_quiz_results.html', {
        'session':          session,
        'attempt':          attempt,
        'attempts':         attempts,
        'rank':             rank,
        'question_results': question_results,
    })


@login_required
def leaderboard(request, pk):
    session    = get_object_or_404(Session, pk=pk)
    is_teacher = request.user.is_teacher and session.group.teacher == request.user
    is_student = request.user.is_student and session.group.students.filter(pk=request.user.pk).exists()
    if not (is_teacher or is_student):
        return HttpResponseForbidden()

    students = session.group.students.all()
    board    = []

    if session.is_quiz:
        # FIX: use QuizAttempt for quiz sessions
        for student in students:
            attempt = QuizAttempt.objects.filter(
                session=session, student=student
            ).first()
            passed = attempt and attempt.status == QuizAttempt.STATUS_FINISHED
            board.append({
                'student':      student,
                'passed':       passed,
                'attempts':     1 if attempt else 0,
                'score':        attempt.score if attempt else 0,
                'total':        attempt.total if attempt else 0,
                'submitted_at': attempt.finished_at if attempt and attempt.finished_at else None,
            })
        board.sort(key=lambda x: (
            not x['passed'],
            -x['score'],
            str(x['submitted_at'] or '9999')
        ))
    else:
        for student in students:
            subs    = Submission.objects.filter(student=student, session=session).order_by('created_at')
            best    = subs.filter(is_correct=True).first()
            board.append({
                'student':      student,
                'passed':       best is not None,
                'attempts':     subs.count(),
                'score':        0,
                'total':        0,
                'submitted_at': best.created_at if best else None,
            })
        board.sort(key=lambda x: (not x['passed'], str(x['submitted_at'] or '9999')))

    return render(request, 'sessions/leaderboard.html', {
        'session': session,
        'board':   board,
    })


def _broadcast_session(session_pk, event_type, data):
    try:
        cl = get_channel_layer()
        async_to_sync(cl.group_send)(
            f'session_{session_pk}',
            {'type': 'session_event', 'event': event_type, 'data': data},
        )
    except Exception:
        pass


def _broadcast_group(group_pk, event_type, data):
    try:
        cl = get_channel_layer()
        async_to_sync(cl.group_send)(
            f'group_session_{group_pk}',
            {'type': 'group_session_event', 'event': event_type, 'data': data},
        )
    except Exception:
        pass