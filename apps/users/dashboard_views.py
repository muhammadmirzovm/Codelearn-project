"""
Dashboard view – shows different content depending on role.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.sessions_app.models import Session
from apps.submissions.models import Submission
from .models import Group


@login_required
def home(request):
    user = request.user

    if user.is_teacher:
        groups = Group.objects.filter(teacher=user).prefetch_related('students')
        upcoming = Session.objects.filter(
            group__teacher=user, start_time__gte=timezone.now()
        ).select_related('group', 'task').order_by('start_time')[:5]
        active = Session.objects.filter(
            group__teacher=user, is_active=True
        ).select_related('group', 'task')
        context = {
            'groups': groups,
            'upcoming_sessions': upcoming,
            'active_sessions': active,
        }
        return render(request, 'users/dashboard_teacher.html', context)
    else:
        # Student
        my_groups = user.student_groups.all()
        upcoming = Session.objects.filter(
            group__in=my_groups, start_time__gte=timezone.now()
        ).select_related('group', 'task').order_by('start_time')[:5]
        active = Session.objects.filter(
            group__in=my_groups, is_active=True
        ).select_related('group', 'task')
        recent_submissions = Submission.objects.filter(
            student=user
        ).select_related('task', 'session').order_by('-created_at')[:10]
        context = {
            'upcoming_sessions': upcoming,
            'active_sessions': active,
            'recent_submissions': recent_submissions,
        }
        return render(request, 'users/dashboard_student.html', context)
