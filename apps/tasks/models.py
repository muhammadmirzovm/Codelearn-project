"""
Tasks app models.
Task: the coding challenge definition.
TestCase: example or hidden test data for evaluation.
"""
from django.db import models
from apps.users.models import User


class Task(models.Model):

    # ── Scope ──────────────────────────────────────────────────────────────
    SCOPE_SESSION = 'session'
    SCOPE_GLOBAL  = 'global'
    SCOPE_CHOICES = [
        (SCOPE_SESSION, 'Session only'),
        (SCOPE_GLOBAL,  'Global challenge'),
    ]

    # ── Difficulty ─────────────────────────────────────────────────────────
    DIFF_EASY   = 'easy'
    DIFF_MEDIUM = 'medium'
    DIFF_HARD   = 'hard'
    DIFF_CHOICES = [
        (DIFF_EASY,   'Easy'),
        (DIFF_MEDIUM, 'Medium'),
        (DIFF_HARD,   'Hard'),
    ]

    # ── Publication status (only for global challenges) ────────────────────
    STATUS_DRAFT     = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED  = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_ARCHIVED,  'Archived'),
    ]

    # ── Core fields (unchanged) ────────────────────────────────────────────
    title          = models.CharField(max_length=200)
    description    = models.TextField(help_text='Markdown-supported problem statement.')
    example_input  = models.TextField(blank=True, help_text='Shown to student as sample input.')
    example_output = models.TextField(blank=True, help_text='Shown to student as expected output.')
    time_limit     = models.PositiveIntegerField(default=5, help_text='Execution time limit in seconds.')
    memory_limit   = models.CharField(max_length=10, default='64m', help_text='Memory limit e.g. 64m.')
    created_by     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    # ── New fields ─────────────────────────────────────────────────────────
    scope       = models.CharField(
        max_length=10, choices=SCOPE_CHOICES, default=SCOPE_SESSION,
        help_text='Session = only used inside a class session. Global = open to everyone.',
    )
    difficulty  = models.CharField(
        max_length=10, choices=DIFF_CHOICES, default=DIFF_EASY, blank=True,
        help_text='Used only for global challenges.',
    )
    coin_reward = models.PositiveIntegerField(
        default=0,
        help_text='Coins awarded on first correct solve. 0 = no reward.',
    )
    status      = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT,
        help_text='Only published global challenges are visible to students.',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    # ── Convenience properties ─────────────────────────────────────────────
    @property
    def example_cases(self):
        return self.test_cases.filter(is_example=True)

    @property
    def hidden_cases(self):
        return self.test_cases.filter(is_example=False)

    @property
    def is_global(self):
        return self.scope == self.SCOPE_GLOBAL

    @property
    def is_published(self):
        return self.status == self.STATUS_PUBLISHED

    @property
    def diff_color(self):
        """Tailwind-compatible CSS class hint for difficulty badge."""
        return {
            self.DIFF_EASY:   'badge-easy',
            self.DIFF_MEDIUM: 'badge-medium',
            self.DIFF_HARD:   'badge-hard',
        }.get(self.difficulty, '')


class TestCase(models.Model):
    """
    A single test case for a task.
    is_example=True  → used for "Run Code" button (student can see input/output).
    is_example=False → used for final "Submit" evaluation (hidden from student).
    """
    task            = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='test_cases')
    input_data      = models.TextField(blank=True, help_text="stdin fed to the student's program.")
    expected_output = models.TextField(help_text='Expected stdout (stripped for comparison).')
    is_example      = models.BooleanField(default=False)
    order           = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        kind = 'Example' if self.is_example else 'Hidden'
        return f'{kind} case #{self.pk} for "{self.task.title}"'