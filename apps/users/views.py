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
from .models import User, Group
from apps.users.models import ChatMessage


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from .models import Notification

from django.http import JsonResponse

from django.contrib.auth import update_session_auth_hash
from .forms import ProfileForm, PasswordChangeForm

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
    if request.user.is_teacher:
        groups = Group.objects.filter(teacher=request.user).prefetch_related('students')
    else:
        groups = request.user.student_groups.all().prefetch_related('students')
    return render(request, 'users/group_list.html', {'groups': groups})


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
    """Teacher regenerates the invite key for a group."""
    group = get_object_or_404(Group, pk=pk, teacher=request.user)
    group.regenerate_key()
    messages.success(request, f'New invite key generated for "{group.name}".')
    return redirect('users:group_list')


@login_required
def join_group(request):
    """Student joins a group using an invite key."""
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
            group.students.add(request.user)
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
@require_POST                          # auto-returns 405 for non-POST
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
                update_session_auth_hash(request, pw_form.user)  # keep session alive
                messages.success(request, '✅ Password changed successfully!')
                return redirect('users:profile')
            else:
                messages.error(request, '❌ Please fix the password errors.')
 
    # Stats
    if user.is_teacher:
        groups_count = user.taught_groups.count()
        students_count = User.objects.filter(
            student_groups__teacher=user
        ).distinct().count()
        submissions_count = None
    else:
        groups_count = user.student_groups.count()
        students_count = None
        # Import here to avoid circular imports
        try:
            from apps.submissions.models import Submission
            submissions_count = Submission.objects.filter(student=user).count()
        except Exception:
            submissions_count = 0
 
    notifications_count = user.notifications.count()
    unread_notif_count  = user.notifications.filter(is_read=False).count()
 
    context = {
        'form':              ProfileForm(instance=user),
        'pw_form':           PasswordChangeForm(user),
        'groups_count':      groups_count,
        'students_count':    students_count,
        'submissions_count': submissions_count,
        'notifications_count': notifications_count,
        'unread_notif_count':  unread_notif_count,
    }
    return render(request, 'users/profile.html', context)