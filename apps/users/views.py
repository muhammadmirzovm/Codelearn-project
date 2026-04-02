"""
Views for user registration, login, and group management.
"""
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST

from .forms import RegisterForm, GroupForm
from .models import User, Group, GroupMembership
from apps.users.models import ChatMessage, Notification

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from .forms import ProfileForm, PasswordChangeForm

import json


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('dashboard:home')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True


def teacher_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher:
            return HttpResponseForbidden('Only teachers can access this page.')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def group_list(request):
    from django.core.cache import cache

    if request.user.is_teacher:
        groups = Group.objects.filter(teacher=request.user).prefetch_related('students')
    else:
        groups = request.user.student_groups.all().prefetch_related('students')

    unread_counts = {}
    for g in groups:
        key = f'chat_unread_{g.id}_{request.user.username}'
        cnt = cache.get(key) or 0
        if cnt:
            unread_counts[g.id] = cnt

    return render(request, 'users/group_list.html', {
        'groups':        groups,
        'unread_counts': unread_counts,
    })


@teacher_required
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.teacher = request.user
            group.save()
            form.save_m2m()
            messages.success(request, f'Group "{group.name}" created.')
            return redirect('users:group_list')
    else:
        form = GroupForm()
    return render(request, 'users/group_form.html', {'form': form, 'title': 'Create Group'})


@teacher_required
def group_edit(request, pk):
    group = get_object_or_404(Group, pk=pk, teacher=request.user)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f'Group "{group.name}" updated.')
            return redirect('users:group_list')
    else:
        form = GroupForm(instance=group)
    return render(request, 'users/group_form.html', {'form': form, 'title': 'Edit Group', 'group': group})


@teacher_required
def group_delete(request, pk):
    group = get_object_or_404(Group, pk=pk, teacher=request.user)
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'Group "{name}" deleted.')
        return redirect('users:group_list')
    return render(request, 'users/group_confirm_delete.html', {'group': group})


@teacher_required
@require_POST
def group_regenerate_key(request, pk):
    group = get_object_or_404(Group, pk=pk, teacher=request.user)
    group.regenerate_key()
    messages.success(request, f'New invite key generated for "{group.name}".')
    return redirect('users:group_list')


@login_required
def join_group(request):
    if request.user.is_teacher:
        messages.error(request, 'Teachers cannot join groups as students.')
        return redirect('dashboard:home')

    if request.method == 'POST':
        key = request.POST.get('invite_key', '').strip()
        try:
            group = Group.objects.get(invite_key=key)
        except (Group.DoesNotExist, ValueError):
            messages.error(request, 'Invalid invite key. Please check and try again.')
            return render(request, 'users/join_group.html')

        if group.students.filter(pk=request.user.pk).exists():
            messages.info(request, f'You are already a member of "{group.name}".')
        else:
            GroupMembership.objects.create(student=request.user, group=group)
            messages.success(request, f'🎉 You joined "{group.name}" successfully!')
        return redirect('dashboard:home')

    return render(request, 'users/join_group.html')


def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    previous_messages = ChatMessage.objects.filter(group=group).select_related('sender').order_by('created_at')[:100]
    return render(request, 'users/group_detail.html', {
        'group': group,
        'previous_messages': previous_messages,
    })


@login_required
@require_POST
def mark_one_read(request, pk):
    Notification.objects.filter(pk=pk, recipient=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def profile(request):
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_info':
            form = ProfileForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, '✅ Profile updated successfully!')
                return redirect('users:profile')
            else:
                messages.error(request, '❌ Please fix the errors below.')

        elif action == 'change_password':
            pw_form = PasswordChangeForm(user, request.POST)
            if pw_form.is_valid():
                pw_form.save()
                update_session_auth_hash(request, pw_form.user)
                messages.success(request, '✅ Password changed successfully!')
                return redirect('users:profile')
            else:
                messages.error(request, '❌ Please fix the password errors.')

    # ── Common ────────────────────────────────────────────────────────────────
    notifications_count = user.notifications.count()
    unread_notif_count  = user.notifications.filter(is_read=False).count()

    # ── Teacher ───────────────────────────────────────────────────────────────
    if user.is_teacher:
        groups_count      = user.taught_groups.count()
        students_count    = User.objects.filter(
            student_groups__teacher=user
        ).distinct().count()
        submissions_count = None
        journal_stats     = None

    # ── Student ───────────────────────────────────────────────────────────────
    else:
        from apps.journals.models import Record

        groups_count   = user.student_groups.count()
        students_count = None

        try:
            from apps.submissions.models import Submission
            submissions_count = Submission.objects.filter(student=user).count()
        except Exception:
            submissions_count = 0

        journal_stats = []
        for group in user.student_groups.select_related('journal').all():
            try:
                journal = group.journal
            except Exception:
                continue

            # Get join date for this student
            try:
                membership = GroupMembership.objects.get(student=user, group=group)
                joined_at = membership.joined_at
            except GroupMembership.DoesNotExist:
                joined_at = None

            # Only count lessons from join date onwards
            all_lessons = journal.lessons.order_by('date')
            if joined_at:
                lessons = all_lessons.filter(date__gte=joined_at)
            else:
                lessons = all_lessons

            lesson_count = lessons.count()
            if lesson_count == 0:
                continue

            records = Record.objects.filter(
                lesson__in=lessons,
                student=user,
            ).select_related('lesson')

            record_map = {r.lesson_id: r for r in records}

            chart_labels = []
            chart_grades = []

            for lesson in lessons:
                rec = record_map.get(lesson.pk)
                chart_labels.append(lesson.date.strftime('%d.%m'))
                if rec and rec.grade is not None:
                    chart_grades.append(rec.grade)
                else:
                    chart_grades.append(None)

            attended    = records.filter(attended=True).count()
            total_grade = sum(r.grade for r in records if r.grade is not None)
            max_score   = lesson_count * 5

            journal_stats.append({
                'group':          group,
                'lesson_count':   lesson_count,
                'attended':       attended,
                'absent':         lesson_count - attended,
                'total_grade':    total_grade,
                'max_score':      max_score,
                'attendance_pct': round(attended / lesson_count * 100) if lesson_count else 0,
                'grade_pct':      round(total_grade / max_score * 100) if max_score else 0,
                'chart_labels':   json.dumps(chart_labels),
                'chart_grades':   json.dumps(chart_grades),
            })

    context = {
        'form':                ProfileForm(instance=user),
        'pw_form':             PasswordChangeForm(user),
        'groups_count':        groups_count,
        'students_count':      students_count,
        'submissions_count':   submissions_count,
        'notifications_count': notifications_count,
        'unread_notif_count':  unread_notif_count,
        'journal_stats':       journal_stats,
    }
    return render(request, 'users/profile.html', context)

@login_required
def select_role(request):
    if request.user.role:
        return redirect('dashboard:home')

    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['teacher', 'student']:
            request.user.role = role
            request.user.save(update_fields=['role'])
            return redirect('dashboard:home')

    return render(request, 'users/select_role.html')