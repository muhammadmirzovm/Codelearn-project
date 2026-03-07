"""
Tasks app models.
Task: the coding challenge definition.
TestCase: example or hidden test data for evaluation.
"""
from django.db import models
from apps.users.models import User


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(help_text='Markdown-supported problem statement.')
    example_input = models.TextField(blank=True, help_text='Shown to student as sample input.')
    example_output = models.TextField(blank=True, help_text='Shown to student as expected output.')
    time_limit = models.PositiveIntegerField(default=5, help_text='Execution time limit in seconds.')
    memory_limit = models.CharField(max_length=10, default='64m', help_text='Memory limit e.g. 64m.')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def example_cases(self):
        return self.test_cases.filter(is_example=True)

    @property
    def hidden_cases(self):
        return self.test_cases.filter(is_example=False)


class TestCase(models.Model):
    """
    A single test case for a task.
    is_example=True  → used for "Run Code" button (student can see input/output).
    is_example=False → used for final "Submit" evaluation (hidden from student).
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(blank=True, help_text='stdin fed to the student\'s program.')
    expected_output = models.TextField(help_text='Expected stdout (stripped for comparison).')
    is_example = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        kind = 'Example' if self.is_example else 'Hidden'
        return f'{kind} case #{self.pk} for "{self.task.title}"'
