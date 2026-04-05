"""
Session management views.
Teachers: create / start / stop sessions, monitor progress.
Students: view active sessions and join coding room.
"""
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Session
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
        ).select_related('group', 'task')
    else:
        sessions = Session.objects.filter(
            group__students=request.user
        ).select_related('group', 'task')
    return render(request, 'sessions/session_list.html', {'sessions': sessions})


@teacher_required
def session_create(request):
    if request.method == 'POST':
        form = SessionForm(request.user, request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, 'Session scheduled.')
            return redirect('sessions:session_list')
    else:
        form = SessionForm(request.user)
    return render(request, 'sessions/session_form.html', {'form': form, 'title': 'Schedule Session'})


@teacher_required
def session_activate(request, pk):
    """Teacher opens the session — store exact activation time for countdown."""
    session = get_object_or_404(Session, pk=pk, group__teacher=request.user)
    from django.utils import timezone
    session.is_active = True
    session.activated_at = timezone.now()
    session.save()

    # Notify clients inside the session room
    _broadcast_session_event(session.pk, 'session_started', {})

    # Notify student dashboards in real-time
    _broadcast_group_event(session.group.pk, 'session_started', {
        'session_pk':       session.pk,
        'task_title':       session.task.title,
        'group_name':       session.group.name,
        'duration_minutes': session.duration_minutes,
        'join_url':         reverse('sessions:join', args=[session.pk]),
        'leaderboard_url':  reverse('sessions:leaderboard', args=[session.pk]),
    })

    messages.success(request, 'Session is now active!')
    return redirect('sessions:monitor', pk=pk)


@teacher_required
def session_deactivate(request, pk):
    """Teacher closes the session."""
    session = get_object_or_404(Session, pk=pk, group__teacher=request.user)
    session.is_active = False
    session.save()

    # Notify clients inside the session room
    _broadcast_session_event(session.pk, 'session_ended', {})

    # Notify student dashboards so the session card disappears
    _broadcast_group_event(session.group.pk, 'session_ended', {
        'session_pk': session.pk,
    })

    messages.success(request, 'Session closed.')
    return redirect('sessions:session_list')


@teacher_required
def session_monitor(request, pk):
    """Live teacher dashboard showing student progress."""
    session = get_object_or_404(Session, pk=pk, group__teacher=request.user)
    students = session.group.students.all()
    student_data = []
    for student in students:
        latest = Submission.objects.filter(
            student=student, session=session
        ).order_by('-created_at').first()
        student_data.append({'student': student, 'submission': latest})
    return render(request, 'sessions/session_monitor.html', {
        'session': session,
        'student_data': student_data,
    })


@login_required
def session_join(request, pk):
    """Student task/code view for an active session."""
    session = get_object_or_404(Session, pk=pk)
    if not request.user.is_student:
        return HttpResponseForbidden('Students only.')
    if not session.can_student_participate(request.user):
        if session.is_time_up:
            messages.warning(request, 'Time is up for this session.')
        else:
            messages.warning(request, 'This session is not active or you are not enrolled.')
        return redirect('sessions:session_list')
    task = session.task
    my_submission = Submission.objects.filter(
        student=request.user, session=session
    ).order_by('-created_at').first()
    activated_at_iso = session.activated_at.isoformat() if session.activated_at else ''
    return render(request, 'sessions/session_join.html', {
        'session': session,
        'task': task,
        'my_submission': my_submission,
        'activated_at_iso': activated_at_iso,
    })


@login_required
def leaderboard(request, pk):
    """Live leaderboard for a session."""
    session = get_object_or_404(Session, pk=pk)
    is_teacher = request.user.is_teacher and session.group.teacher == request.user
    is_student = request.user.is_student and session.group.students.filter(pk=request.user.pk).exists()
    if not (is_teacher or is_student):
        return HttpResponseForbidden()
    students = session.group.students.all()
    board = []
    for student in students:
        subs = Submission.objects.filter(student=student, session=session).order_by('created_at')
        attempts = subs.count()
        best = subs.filter(is_correct=True).first()
        board.append({
            'student': student,
            'attempts': attempts,
            'passed': best is not None,
            'submitted_at': best.created_at if best else None,
        })
    board.sort(key=lambda x: (not x['passed'], x['submitted_at'] or '9999'))
    return render(request, 'sessions/leaderboard.html', {'session': session, 'board': board})


# ── Helpers ──────────────────────────────────────────────────────────────────

def _broadcast_session_event(session_pk, event_type, data):
    """Broadcast to all clients connected to a specific session room."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'session_{session_pk}',
            {'type': 'session_event', 'event': event_type, 'data': data},
        )
    except Exception:
        pass


def _broadcast_group_event(group_pk, event_type, data):
    """
    Broadcast to all students connected to a group's dashboard channel.
    Used so student dashboards update in real-time when a session starts/ends.
    """
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'group_session_{group_pk}',
            {'type': 'group_session_event', 'event': event_type, 'data': data},
        )
    except Exception:
        pass