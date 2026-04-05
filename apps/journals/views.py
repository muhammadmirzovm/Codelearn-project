# apps/journals/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, CreateView, View
from django.http import JsonResponse
import json

from apps.users.models import Group, GroupMembership
from apps.journals.models import Journal, Lesson, Record
from apps.journals.forms import LessonForm


def get_or_create_membership(student, group):
    """
    Returns GroupMembership for a student in a group.
    If missing (e.g. student existed before GroupMembership model was added),
    creates one using the group's creation date so they're counted from day one.
    """
    membership, _ = GroupMembership.objects.get_or_create(
        student=student,
        group=group,
        defaults={'joined_at': group.created_at.date()}
    )
    return membership


def build_membership_map(group):
    """
    Returns a dict {student_id: joined_at} for all current students in the group.
    Auto-creates missing memberships so every student has a consistent join date.
    """
    result = {}
    for student in group.students.all():
        m = get_or_create_membership(student, group)
        result[student.pk] = m
    return result


def ensure_records_for_lesson(lesson, group):
    """
    Creates a Record only for students who were in the group
    on or before the lesson date (joined_at <= lesson.date).
    Students who joined after the lesson date are excluded — they
    were not part of the group at that time.
    Safe to call multiple times (get_or_create).
    """
    for student in group.students.all():
        membership = get_or_create_membership(student, group)
        if membership.joined_at <= lesson.date:
            Record.objects.get_or_create(
                lesson=lesson,
                student=student,
                defaults={'grade': 0, 'attended': False}
            )


class JournalDetailView(LoginRequiredMixin, DetailView):
    model = Journal
    template_name = 'journals/journal_detail.html'
    context_object_name = 'journal'

    def get_object(self):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        user = self.request.user
        if user != group.teacher and user not in group.students.all():
            raise PermissionDenied
        journal, _ = Journal.objects.get_or_create(group=group)
        return journal

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        journal = self.object
        user = self.request.user
        lessons = journal.lessons.all()

        # Overall journal stats (top stats bar)
        lesson_count = lessons.count()
        max_score = lesson_count * 5

        # Build membership map — auto-fixes students with missing memberships
        membership_map = build_membership_map(journal.group)

        student_stats = []
        for student in journal.group.students.all():
            membership = membership_map.get(student.pk)
            joined_date = membership.joined_at if membership else None

            # Only count lessons from join date onwards
            student_lessons = lessons.filter(date__gte=joined_date) if joined_date else lessons

            student_lesson_count = student_lessons.count()
            student_max_score = student_lesson_count * 5

            records = Record.objects.filter(lesson__in=student_lessons, student=student)
            total_grade = sum(r.grade for r in records if r.grade is not None)
            attended_count = records.filter(attended=True).count()
            percentage = round((total_grade / student_max_score) * 100) if student_max_score > 0 else 0

            student_stats.append({
                'student': student,
                'membership': membership,
                'joined_date': joined_date,
                'total_grade': total_grade,
                'attended': attended_count,
                'lesson_count': student_lesson_count,
                'max_score': student_max_score,
                'percentage': percentage,
            })

        ctx['lessons'] = lessons
        ctx['lesson_count'] = lesson_count
        ctx['max_score'] = max_score
        ctx['student_stats'] = student_stats
        ctx['is_teacher'] = user == journal.group.teacher
        return ctx


class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'journals/lesson_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        if request.user != self.group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        lesson = form.save(commit=False)
        lesson.journal = self.group.journal
        lesson.save()
        ensure_records_for_lesson(lesson, self.group)
        return redirect('journals:record-edit', lesson_pk=lesson.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['group'] = self.group
        return ctx


class RecordUpdateView(LoginRequiredMixin, View):
    """Teacher edits grade, attendance, and comment for every student in a lesson."""

    def dispatch(self, request, *args, **kwargs):
        self.lesson = get_object_or_404(
            Lesson.objects.select_related('journal__group'),
            pk=self.kwargs['lesson_pk']
        )
        if request.user != self.lesson.journal.group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        group = self.lesson.journal.group

        # Create records only for eligible students (joined on or before lesson date)
        ensure_records_for_lesson(self.lesson, group)

        # Remove any stale records for students who joined AFTER this lesson
        for student in group.students.all():
            membership = get_or_create_membership(student, group)
            if membership.joined_at > self.lesson.date:
                Record.objects.filter(lesson=self.lesson, student=student).delete()

        records = (Record.objects
                   .filter(lesson=self.lesson)
                   .select_related('student')
                   .order_by('student__username'))
        return render(request, 'journals/record_form.html', {
            'lesson': self.lesson,
            'records': records,
            'group_pk': group.pk,
        })

    def post(self, request, *args, **kwargs):
        records = (Record.objects
                   .filter(lesson=self.lesson)
                   .select_related('student'))
        for record in records:
            record.attended = f'attended_{record.pk}' in request.POST
            grade_val = request.POST.get(f'grade_{record.pk}', '0').strip()
            record.grade = int(grade_val) if grade_val != '' else 0
            record.comment = request.POST.get(f'comment_{record.pk}', '')
            record.save()
        return redirect('journals:detail', group_pk=self.lesson.journal.group.pk)


class MembershipUpdateView(LoginRequiredMixin, View):
    """
    Teacher updates a student's join date for a group.
    Changing the join date changes which lessons count toward that student's score.
    POST body: { "joined_at": "YYYY-MM-DD" }
    """

    def dispatch(self, request, *args, **kwargs):
        self.membership = get_object_or_404(
            GroupMembership.objects.select_related('group__teacher', 'student'),
            pk=self.kwargs['membership_pk']
        )
        if request.user != self.membership.group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            new_date = data.get('joined_at', '').strip()
            if not new_date:
                return JsonResponse({'error': 'Date is required.'}, status=400)
            # Use .update() to bypass auto_now_add restriction
            GroupMembership.objects.filter(pk=self.membership.pk).update(joined_at=new_date)
            return JsonResponse({'success': True, 'joined_at': new_date})
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({'error': str(e)}, status=400)


class LessonUpdateView(LoginRequiredMixin, View):
    """Teacher edits a lesson's title, topic, and date."""

    def dispatch(self, request, *args, **kwargs):
        self.lesson = get_object_or_404(
            Lesson.objects.select_related('journal__group'),
            pk=self.kwargs['lesson_pk']
        )
        if request.user != self.lesson.journal.group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = LessonForm(instance=self.lesson)
        return render(request, 'journals/lesson_form.html', {
            'form': form,
            'group': self.lesson.journal.group,
            'lesson': self.lesson,
            'editing': True,
        })

    def post(self, request, *args, **kwargs):
        form = LessonForm(request.POST, instance=self.lesson)
        if form.is_valid():
            form.save()
            return redirect('journals:detail', group_pk=self.lesson.journal.group.pk)
        return render(request, 'journals/lesson_form.html', {
            'form': form,
            'group': self.lesson.journal.group,
            'lesson': self.lesson,
            'editing': True,
        })


class LessonDeleteView(LoginRequiredMixin, View):
    """Teacher deletes a lesson and all its records."""

    def dispatch(self, request, *args, **kwargs):
        self.lesson = get_object_or_404(
            Lesson.objects.select_related('journal__group'),
            pk=self.kwargs['lesson_pk']
        )
        if request.user != self.lesson.journal.group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Confirmation page before deleting."""
        return render(request, 'journals/lesson_confirm_delete.html', {
            'lesson': self.lesson,
            'group_pk': self.lesson.journal.group.pk,
        })

    def post(self, request, *args, **kwargs):
        group_pk = self.lesson.journal.group.pk
        self.lesson.delete()  # cascades to all Records
        return redirect('journals:detail', group_pk=group_pk)