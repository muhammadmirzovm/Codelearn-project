"""
Forms for task creation and test case management.
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Task, TestCase

CSS  = 'inp'
MONO = 'inp mono'


class TaskForm(forms.ModelForm):
    class Meta:
        model  = Task
        fields = (
            'title', 'description',
            'example_input', 'example_output',
            'time_limit', 'memory_limit',
            # ── Global challenge fields ──────────────────────────────────
            'scope', 'difficulty', 'coin_reward', 'status',
        )
        widgets = {
            'title':          forms.TextInput(attrs={'class': CSS,  'placeholder': 'Task title'}),
            'description':    forms.Textarea( attrs={'class': MONO, 'rows': 7, 'placeholder': 'Problem statement…'}),
            'example_input':  forms.Textarea( attrs={'class': MONO, 'rows': 4, 'placeholder': 'Sample stdin'}),
            'example_output': forms.Textarea( attrs={'class': MONO, 'rows': 4, 'placeholder': 'Expected stdout'}),
            'time_limit':     forms.NumberInput(attrs={'class': CSS, 'min': 1, 'max': 30}),
            'memory_limit':   forms.TextInput(attrs={'class': CSS,  'placeholder': '64m'}),
            # ── New ─────────────────────────────────────────────────────
            'scope':       forms.Select(attrs={'class': CSS}),
            'difficulty':  forms.Select(attrs={'class': CSS}),
            'coin_reward': forms.NumberInput(attrs={'class': CSS, 'min': 0, 'max': 9999}),
            'status':      forms.Select(attrs={'class': CSS}),
        }
        help_texts = {
            'scope':       'Global = open to all users and appears in the Challenges page.',
            'difficulty':  'Used only for global challenges.',
            'coin_reward': 'Coins awarded on first correct solve. Set 0 for no reward.',
            'status':      'Only Published global challenges are visible to students.',
        }

    def clean(self):
        cleaned = super().clean()
        scope       = cleaned.get('scope')
        coin_reward = cleaned.get('coin_reward')
        status      = cleaned.get('status')

        # Warn if someone accidentally publishes a session task
        if scope == Task.SCOPE_SESSION and status == Task.STATUS_PUBLISHED:
            self.add_error(
                'status',
                'Status "Published" only applies to global challenges. '
                'Session tasks do not need a status.',
            )

        # Prevent non-zero coin reward on session tasks
        if scope == Task.SCOPE_SESSION and coin_reward and coin_reward > 0:
            self.add_error(
                'coin_reward',
                'Coin rewards only apply to global challenges.',
            )

        return cleaned


class TestCaseForm(forms.ModelForm):
    class Meta:
        model  = TestCase
        fields = ('input_data', 'expected_output', 'is_example', 'order')
        widgets = {
            'input_data':      forms.Textarea(  attrs={'class': MONO, 'rows': 3, 'placeholder': 'stdin'}),
            'expected_output': forms.Textarea(  attrs={'class': MONO, 'rows': 3, 'placeholder': 'expected stdout'}),
            'is_example':      forms.CheckboxInput(attrs={'class': ''}),
            'order':           forms.NumberInput(  attrs={'class': 'inp', 'style': 'width:70px;'}),
        }


TestCaseFormSet = inlineformset_factory(
    Task, TestCase, form=TestCaseForm, extra=2, can_delete=True,
)