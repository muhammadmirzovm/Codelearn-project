"""
Users app models.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.conf import settings


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

    @property
    def coin_balance(self):
        """Live coin balance computed from the immutable transaction ledger."""
        result = self.coin_transactions.aggregate(total=Sum('amount'))
        return result['total'] or 0

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class Group(models.Model):
    """A group of students managed by one teacher."""
    name    = models.CharField(max_length=100)
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


class ChatMessage(models.Model):
    group      = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    TYPE_CHOICES = [
        ('info',    '💡 Info'),
        ('success', '✅ Success'),
        ('warning', '⚠️ Warning'),
        ('danger',  '❌ Danger'),
    ]

    recipient  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title      = models.CharField(max_length=255)
    message    = models.TextField(blank=True)
    notif_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} → {self.recipient.username}'


class CoinTransaction(models.Model):
    """
    Immutable ledger of all coin movements.
    Never update or delete rows — only append.
    The user's balance is always SUM(amount) for their rows.
    """
    TYPE_EARN  = 'earn'
    TYPE_SPEND = 'spend'
    TYPE_CHOICES = [
        (TYPE_EARN,  'Earned'),
        (TYPE_SPEND, 'Spent'),
    ]

    user           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coin_transactions',
    )
    # Positive = coins in (earn), negative = coins out (spend)
    amount         = models.IntegerField()
    tx_type        = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_EARN)
    # Optional link back to the submission that triggered this transaction
    ref_submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='coin_transactions',
    )
    note       = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f'{sign}{self.amount} coins → {self.user.username} ({self.note})'