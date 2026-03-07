"""
Forms for task creation and test case management.
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Task, TestCase

CSS = 'inp'
MONO = 'inp mono'


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'example_input', 'example_output', 'time_limit', 'memory_limit')
        widgets = {
            'title': forms.TextInput(attrs={'class': CSS, 'placeholder': 'Task title'}),
            'description': forms.Textarea(attrs={'class': MONO, 'rows': 7, 'placeholder': 'Problem statement…'}),
            'example_input': forms.Textarea(attrs={'class': MONO, 'rows': 4, 'placeholder': 'Sample stdin'}),
            'example_output': forms.Textarea(attrs={'class': MONO, 'rows': 4, 'placeholder': 'Expected stdout'}),
            'time_limit': forms.NumberInput(attrs={'class': CSS, 'min': 1, 'max': 30}),
            'memory_limit': forms.TextInput(attrs={'class': CSS, 'placeholder': '64m'}),
        }


class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ('input_data', 'expected_output', 'is_example', 'order')
        widgets = {
            'input_data': forms.Textarea(attrs={'class': MONO, 'rows': 3, 'placeholder': 'stdin'}),
            'expected_output': forms.Textarea(attrs={'class': MONO, 'rows': 3, 'placeholder': 'expected stdout'}),
            'is_example': forms.CheckboxInput(attrs={'class': ''}),
            'order': forms.NumberInput(attrs={'class': 'inp', 'style': 'width:70px;'}),
        }


TestCaseFormSet = inlineformset_factory(
    Task, TestCase, form=TestCaseForm, extra=2, can_delete=True,
)
