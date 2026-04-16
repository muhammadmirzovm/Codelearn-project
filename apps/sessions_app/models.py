from django.db import models
from django.utils import timezone
from apps.users.models import User, Group
from apps.tasks.models import Task


class Session(models.Model):
    TYPE_ALGORITHMIC = 'algorithmic'
    TYPE_QUIZ        = 'quiz'
    TYPE_CHOICES = [
        (TYPE_ALGORITHMIC, 'Algorithmic'),
        (TYPE_QUIZ,        'Quiz'),
    ]

    group        = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions')
    task         = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    test_pack    = models.ForeignKey('tests_app.TestPack', on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    session_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ALGORITHMIC)
    start_time   = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=0, help_text='0 = no time limit.')
    is_active    = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f'{self.group.name} – {self.title} @ {self.start_time:%Y-%m-%d %H:%M}'

    @property
    def is_quiz(self):
        return self.session_type == self.TYPE_QUIZ

    @property
    def title(self):
        if self.task:      return self.task.title
        if self.test_pack: return self.test_pack.title
        return '—'

    @property
    def end_time(self):
        if self.duration_minutes and self.activated_at:
            from datetime import timedelta
            return self.activated_at + timedelta(minutes=self.duration_minutes)
        return None

    @property
    def seconds_remaining(self):
        end = self.end_time
        if end is None: return None
        return max(0, int((end - timezone.now()).total_seconds()))

    @property
    def is_time_up(self):
        sr = self.seconds_remaining
        return sr is not None and sr <= 0

    @property
    def has_started(self):
        return timezone.now() >= self.start_time

    def can_student_participate(self, user):
        return (
            self.is_active
            and self.group.students.filter(pk=user.pk).exists()
            and not self.is_time_up
        )


class QuizAttempt(models.Model):
    """Tracks a student's quiz attempt within a session."""
    STATUS_ONGOING  = 'ongoing'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES  = [
        (STATUS_ONGOING,  'Ongoing'),
        (STATUS_FINISHED, 'Finished'),
    ]

    session     = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='quiz_attempts')
    student     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ONGOING)
    score       = models.PositiveIntegerField(default=0)
    total       = models.PositiveIntegerField(default=0)
    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    coins_awarded = models.BooleanField(default=False)

    class Meta:
        unique_together = ('session', 'student')
        ordering        = ['-score', 'finished_at']

    def __str__(self):
        return f'{self.student.username} — {self.session}'

    @property
    def percentage(self):
        return round((self.score / self.total) * 100) if self.total > 0 else 0

    @property
    def time_taken_seconds(self):
        if self.finished_at and self.started_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None


class QuizAnswer(models.Model):
    """One answer by a student for one question in a session quiz."""
    attempt    = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question   = models.ForeignKey('tests_app.Question', on_delete=models.CASCADE)
    choice     = models.ForeignKey('tests_app.Choice', on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('attempt', 'question')