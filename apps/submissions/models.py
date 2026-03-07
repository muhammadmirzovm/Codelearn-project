"""
Submissions app models.
Submission: a student's code attempt against a task within a session.
"""
from django.db import models
from apps.users.models import User
from apps.tasks.models import Task


class Submission(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_PASSED = 'passed'
    STATUS_FAILED = 'failed'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_PASSED, 'Passed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_ERROR, 'Error'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    # Link to session so leaderboard is per-session
    session = models.ForeignKey(
        'sessions_app.Session',
        on_delete=models.CASCADE,
        related_name='submissions',
        null=True, blank=True,
    )
    code = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    # JSON: list of per-test-case results
    results = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Submission #{self.pk} by {self.student.username} [{self.status}]'

    @property
    def passed_count(self):
        return sum(1 for r in self.results if r.get('passed'))

    @property
    def total_count(self):
        return len(self.results)
