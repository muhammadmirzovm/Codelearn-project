"""
Submissions app models.
"""
from django.db import models
from apps.users.models import User
from apps.tasks.models import Task


class Submission(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_PASSED  = 'passed'
    STATUS_FAILED  = 'failed'
    STATUS_ERROR   = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_PASSED,  'Passed'),
        (STATUS_FAILED,  'Failed'),
        (STATUS_ERROR,   'Error'),
    ]

    LANG_PYTHON     = 'python'
    LANG_JAVASCRIPT = 'javascript'
    LANG_CPP        = 'cpp'
    LANG_C          = 'c'
    LANG_CHOICES = [
        (LANG_PYTHON,     'Python'),
        (LANG_JAVASCRIPT, 'JavaScript'),
        (LANG_CPP,        'C++'),
        (LANG_C,          'C'),
    ]

    student  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    task     = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    session  = models.ForeignKey(
        'sessions_app.Session',
        on_delete=models.CASCADE,
        related_name='submissions',
        null=True, blank=True,
    )
    code          = models.TextField()
    language      = models.CharField(max_length=20, choices=LANG_CHOICES, default=LANG_PYTHON)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_correct    = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    evaluated_at  = models.DateTimeField(null=True, blank=True)
    results       = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Submission #{self.pk} by {self.student.username} [{self.language}] [{self.status}]'

    @property
    def passed_count(self):
        return sum(1 for r in self.results if r.get('passed'))

    @property
    def total_count(self):
        return len(self.results)


class SolvedChallenge(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solved_challenges')
    task          = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='solved_challenges')
    submission    = models.ForeignKey(Submission, on_delete=models.SET_NULL, null=True, related_name='solve_record')
    coins_awarded = models.PositiveIntegerField(default=0)
    solved_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'task')
        ordering = ['-solved_at']

    def __str__(self):
        return f'{self.user.username} solved "{self.task.title}" (+{self.coins_awarded} coins)'