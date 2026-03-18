from django.db import models
from django.conf import settings


class Ticket(models.Model):
    CATEGORY_CHOICES = [
        ('bug',        '🐛 Bug report'),
        ('question',   '❓ Question'),
        ('suggestion', '💡 Suggestion'),
        ('other',      '📌 Other'),
    ]
    STATUS_CHOICES = [
        ('open',        '🟡 Open'),
        ('in_progress', '🔵 In Progress'),
        ('closed',      '✅ Closed'),
    ]

    sender   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets',
    )
    title    = models.CharField(max_length=200)
    message  = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='question')
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES,   default='open')
    reply    = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_status_display()}] {self.title} — {self.sender.username}'