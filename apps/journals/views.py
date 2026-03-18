# apps/journals/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, CreateView, View

from apps.users.models import Group
from apps.journals.models import Journal, Lesson, Record
from apps.journals.forms import LessonForm


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
        students = journal.group.students.all()
        lesson_count = lessons.count()
        max_score = lesson_count * 5

        student_stats = []
        for student in students:
            total_grade = sum(
                r.grade for r in Record.objects.filter(
                    lesson__journal=journal,
                    student=student,
                    grade__isnull=False
                )
            )
            attended = Record.objects.filter(
                lesson__journal=journal,
                student=student,
                attended=True
            ).count()
            percentage = round((total_grade / max_score) * 100) if max_score > 0 else 0
            student_stats.append({
                'student': student,
                'total_grade': total_grade,
                'attended': attended,
                'percentage': percentage,
            })

        ctx['lessons'] = lessons
        ctx['student_stats'] = student_stats
        ctx['lesson_count'] = lesson_count
        ctx['max_score'] = max_score
        ctx['is_teacher'] = user == journal.group.teacher
        return ctx


class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'journals/lesson_form.html'

    def dispatch(self, request, *args, **kwargs):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        if request.user != group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        group = get_object_or_404(Group, pk=self.kwargs['group_pk'])
        lesson = form.save(commit=False)
        lesson.journal = group.journal
        lesson.save()

        # Auto-create a record for every student with grade=0, attended=False
        for student in group.students.all():
            Record.objects.get_or_create(
                lesson=lesson,
                student=student,
                defaults={'grade': 0, 'attended': False}
            )

        return redirect('journals:detail', group_pk=self.kwargs['group_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['group_pk'] = self.kwargs['group_pk']
        return ctx


class RecordUpdateView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        self.lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_pk'])
        if request.user != self.lesson.journal.group.teacher:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        group = self.lesson.journal.group

        # Create missing records for any student who doesn't have one yet
        for student in group.students.all():
            Record.objects.get_or_create(
                lesson=self.lesson,
                student=student,
                defaults={'grade': 0, 'attended': False}
            )

        records = Record.objects.filter(
            lesson=self.lesson
        ).select_related('student').order_by('student__username')

        return render(request, 'journals/record_form.html', {
            'lesson': self.lesson,
            'records': records,
            'group_pk': group.pk,
        })

    def post(self, request, *args, **kwargs):
        records = Record.objects.filter(
            lesson=self.lesson
        ).select_related('student')

        for record in records:
            attended = f'attended_{record.pk}' in request.POST
            grade_val = request.POST.get(f'grade_{record.pk}', '0')

            record.attended = attended
            # Absent students automatically get 0
            record.grade = int(grade_val) if grade_val != '' else 0
            record.comment = request.POST.get(f'comment_{record.pk}', '')
            record.save()

        return redirect('journals:detail', group_pk=self.lesson.journal.group.pk)