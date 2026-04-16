from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.core.cache import cache
from apps.sessions_app.models import Session
from apps.submissions.models import Submission
from .models import Group


def _get_unread_counts(user, groups):
    result = {}
    for g in groups:
        key = f'chat_unread_{g.id}_{user.username}'
        count = cache.get(key) or 0
        if count:
            result[g.id] = count
    return result


def _auto_close_expired(sessions):
    """
    Automatically mark sessions as inactive if their time is up.
    This handles the case where teacher never manually closed the session.
    """
    now = timezone.now()
    for session in sessions:
        if session.is_active and session.is_time_up:
            Session.objects.filter(pk=session.pk).update(is_active=False)
            # Broadcast session_ended so connected clients are notified
            try:
                from apps.sessions_app.views import _broadcast_session, _broadcast_group
                _broadcast_session(session.pk, 'session_ended', {})
                _broadcast_group(session.group.pk, 'session_ended', {'session_pk': session.pk})
            except Exception:
                pass


@login_required
def home(request):
    user = request.user

    if user.is_teacher:
        groups = Group.objects.filter(teacher=user).prefetch_related('students')

        # Get all active sessions first, then auto-close expired ones
        all_active = list(Session.objects.filter(
            group__teacher=user, is_active=True
        ).select_related('group', 'task', 'test_pack'))
        _auto_close_expired(all_active)

        # Re-query after auto-close
        active = Session.objects.filter(
            group__teacher=user, is_active=True
        ).select_related('group', 'task', 'test_pack')

        upcoming = Session.objects.filter(
            group__teacher=user,
            is_active=False,
            activated_at__isnull=True,
        ).select_related('group', 'task', 'test_pack').order_by('start_time')[:5]

        context = {
            'groups':            groups,
            'upcoming_sessions': upcoming,
            'active_sessions':   active,
            'unread_counts':     _get_unread_counts(user, groups),
        }
        return render(request, 'users/dashboard_teacher.html', context)

    else:
        my_groups = user.student_groups.prefetch_related('students').select_related('teacher').all()

        # Get all active sessions first, then auto-close expired ones
        all_active = list(Session.objects.filter(
            group__in=my_groups, is_active=True
        ).select_related('group', 'task', 'test_pack'))
        _auto_close_expired(all_active)

        # Re-query after auto-close
        active = Session.objects.filter(
            group__in=my_groups, is_active=True
        ).select_related('group', 'task', 'test_pack')

        upcoming = Session.objects.filter(
            group__in=my_groups,
            is_active=False,
            activated_at__isnull=True,
        ).select_related('group', 'task', 'test_pack').order_by('start_time')[:5]

        recent_submissions = Submission.objects.filter(
            student=user
        ).select_related('task', 'session').order_by('-created_at')[:10]

        context = {
            'upcoming_sessions':  upcoming,
            'active_sessions':    active,
            'recent_submissions': recent_submissions,
            'unread_counts':      _get_unread_counts(user, my_groups),
        }
        return render(request, 'users/dashboard_student.html', context)