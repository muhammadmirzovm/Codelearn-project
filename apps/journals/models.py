from django.db import models
from apps.users.models import Group, User


class Journal(models.Model):
    """One journal per group — auto-created when a group is created."""
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name='journal'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Journal — {self.group.name}'


class Lesson(models.Model):
    """A single class session recorded in a journal."""
    journal = models.ForeignKey(
        Journal, on_delete=models.CASCADE, related_name='lessons'
    )
    title = models.CharField(max_length=200)
    topic = models.TextField(blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.title} ({self.date})'


class Record(models.Model):
    """Grade + attendance for one student in one lesson."""
    GRADE_CHOICES = [(i, str(i)) for i in range(0, 6)]

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name='records'
    )
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='journal_records',
        limit_choices_to={'role': User.STUDENT},
    )
    grade = models.PositiveSmallIntegerField(
        choices=GRADE_CHOICES, null=True, blank=True
    )
    attended = models.BooleanField(default=True)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('lesson', 'student')  # one record per student per lesson

    def __str__(self):
        status = 'present' if self.attended else 'absent'
        return f'{self.student.username} — {self.lesson.title} [{status}]'