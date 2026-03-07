from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.forms import inlineformset_factory

from .models import Task, TestCase
from .forms import TaskForm, TestCaseForm


def teacher_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher:
            return HttpResponseForbidden('Teachers only.')
        return view_func(request, *args, **kwargs)
    return wrapper


def _make_formset(extra=0):
    return inlineformset_factory(
        Task, TestCase, form=TestCaseForm,
        extra=extra, can_delete=True, max_num=None,
    )


@teacher_required
def task_list(request):
    tasks = Task.objects.filter(created_by=request.user).prefetch_related('test_cases')
    return render(request, 'tasks/task_list.html', {'tasks': tasks})


@teacher_required
def task_create(request):
    FormSet = _make_formset(extra=0)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        formset = FormSet(request.POST, prefix='testcase_set')
        if form.is_valid() and formset.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            formset.instance = task
            formset.save()
            messages.success(request, f'Task "{task.title}" created!')
            return redirect('tasks:task_list')
    else:
        form = TaskForm()
        formset = FormSet(prefix='testcase_set')
    return render(request, 'tasks/task_form.html', {
        'form': form, 'formset': formset, 'title': 'Create Task'
    })


@teacher_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, created_by=request.user)
    FormSet = _make_formset(extra=0)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        formset = FormSet(request.POST, instance=task, prefix='testcase_set')
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Task "{task.title}" updated!')
            return redirect('tasks:task_list')
    else:
        form = TaskForm(instance=task)
        formset = FormSet(instance=task, prefix='testcase_set')
    return render(request, 'tasks/task_form.html', {
        'form': form, 'formset': formset, 'title': f'Edit Task — {task.title}'
    })


@teacher_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, created_by=request.user)
    if request.method == 'POST':
        name = task.title
        task.delete()
        messages.success(request, f'Task "{name}" deleted.')
        return redirect('tasks:task_list')
    return render(request, 'tasks/task_confirm_delete.html', {'task': task})
