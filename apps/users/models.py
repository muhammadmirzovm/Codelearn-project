"""
Users app models.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    TEACHER = 'teacher'
    STUDENT = 'student'
    ROLE_CHOICES = [
        (TEACHER, 'Teacher'),
        (STUDENT, 'Student'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=STUDENT)

    @property
    def is_teacher(self):
        return self.role == self.TEACHER

    @property
    def is_student(self):
        return self.role == self.STUDENT

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class Group(models.Model):
    """A group of students managed by one teacher."""
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='taught_groups',
        limit_choices_to={'role': User.TEACHER},
    )
    students = models.ManyToManyField(
        User, blank=True,
        related_name='student_groups',
        limit_choices_to={'role': User.STUDENT},
    )
    invite_key = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        help_text='Students paste this key to join the group.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'teacher')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} (by {self.teacher.username})'

    def regenerate_key(self):
        self.invite_key = uuid.uuid4()
        self.save(update_fields=['invite_key'])
