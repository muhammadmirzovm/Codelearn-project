"""
Sessions app models.
"""
from django.db import models
from django.utils import timezone
from apps.users.models import User, Group
from apps.tasks.models import Task


class Session(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(
        default=0, help_text='Session duration in minutes. 0 = no time limit.'
    )
    is_active = models.BooleanField(default=False)
    activated_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Exact moment teacher clicked Start — used for countdown timer.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f'{self.group.name} – {self.task.title} @ {self.start_time:%Y-%m-%d %H:%M}'

    @property
    def has_started(self):
        return timezone.now() >= self.start_time

    @property
    def end_time(self):
        """Returns when session timer expires, or None if unlimited."""
        if self.duration_minutes and self.activated_at:
            from datetime import timedelta
            return self.activated_at + timedelta(minutes=self.duration_minutes)
        return None

    @property
    def seconds_remaining(self):
        end = self.end_time
        if end is None:
            return None
        return max(0, int((end - timezone.now()).total_seconds()))

    @property
    def is_time_up(self):
        sr = self.seconds_remaining
        return sr is not None and sr <= 0

    def can_student_participate(self, user: User) -> bool:
        return (
            self.is_active
            and self.group.students.filter(pk=user.pk).exists()
            and not self.is_time_up
        )
