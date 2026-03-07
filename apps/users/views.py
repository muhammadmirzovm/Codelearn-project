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
