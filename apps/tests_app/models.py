from django.db import models
from apps.users.models import User, Group


class TestPack(models.Model):
    MODE_SESSION = 'session'
    MODE_GLOBAL  = 'global'
    MODE_CHOICES = [
        (MODE_SESSION, 'Session uchun'),
        (MODE_GLOBAL,  'Global (har doim mavjud)'),
    ]

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    mode        = models.CharField(max_length=10, choices=MODE_CHOICES, default=MODE_SESSION)
    created_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_packs')
    # Global mode only
    duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text='Faqat Global test uchun. 0 = vaqt cheklovsiz.'
    )
    coin_reward = models.PositiveIntegerField(
        default=0,
        help_text='Faqat Global test uchun. Max 5. Faqat 100% to\'g\'ri bo\'lsa beriladi.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_mode_display()}] {self.title}'

    @property
    def is_global(self):
        return self.mode == self.MODE_GLOBAL

    @property
    def question_count(self):
        return self.questions.count()


class Question(models.Model):
    test_pack = models.ForeignKey(TestPack, on_delete=models.CASCADE, related_name='questions')
    text      = models.TextField()
    order     = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Q{self.order}: {self.text[:50]}'


class Choice(models.Model):
    LABELS = ['A', 'B', 'C', 'D']

    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text       = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    label      = models.CharField(max_length=1, default='A')

    class Meta:
        ordering = ['label']

    def __str__(self):
        return f'{self.label}: {self.text}'


class GlobalTestAttempt(models.Model):
    """Tracks student attempts on global (always-available) tests."""
    STATUS_ONGOING  = 'ongoing'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES  = [
        (STATUS_ONGOING,  'Ongoing'),
        (STATUS_FINISHED, 'Finished'),
    ]

    test_pack   = models.ForeignKey(TestPack, on_delete=models.CASCADE, related_name='global_attempts')
    student     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='global_test_attempts')
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ONGOING)
    score       = models.PositiveIntegerField(default=0)
    total       = models.PositiveIntegerField(default=0)
    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    coins_awarded = models.BooleanField(default=False)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.student.username} — {self.test_pack.title}'

    @property
    def percentage(self):
        return round((self.score / self.total) * 100) if self.total > 0 else 0

    @property
    def time_taken_seconds(self):
        if self.finished_at and self.started_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None


class GlobalTestAnswer(models.Model):
    attempt    = models.ForeignKey(GlobalTestAttempt, on_delete=models.CASCADE, related_name='answers')
    question   = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice     = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        unique_together = ('attempt', 'question')