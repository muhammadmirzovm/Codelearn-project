from django import forms
from .models import Session
from apps.tasks.models import Task
from apps.users.models import Group


class SessionForm(forms.ModelForm):
    SESSION_TYPE_CHOICES = [
        ('algorithmic', '⚡ Algorithmic — kod yechish masalasi'),
        ('quiz',        '🧪 Quiz — test savollari'),
    ]
    session_type = forms.ChoiceField(
        choices=SESSION_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='algorithmic',
        label='Session turi',
    )

    class Meta:
        model  = Session
        fields = ('group', 'session_type', 'task', 'test_pack', 'start_time', 'duration_minutes')
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'duration_minutes': forms.NumberInput(attrs={
                'min': 0, 'max': 300, 'placeholder': '0 = cheklovsiz'
            }),
        }

    def __init__(self, teacher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.tests_app.models import TestPack
        self.fields['group'].queryset     = Group.objects.filter(teacher=teacher)
        self.fields['task'].queryset      = Task.objects.all()
        self.fields['task'].required      = False
        self.fields['task'].label         = '⚡ Algorithmic masala'
        self.fields['test_pack'].queryset = TestPack.objects.all()
        self.fields['test_pack'].required = False
        self.fields['test_pack'].label    = '🧪 Test paketi'
        self.fields['duration_minutes'].help_text = '0 = vaqt cheklovsiz'

    def clean(self):
        cleaned = super().clean()
        stype     = cleaned.get('session_type')
        task      = cleaned.get('task')
        test_pack = cleaned.get('test_pack')
        if stype == 'algorithmic' and not task:
            self.add_error('task', 'Algorithmic session uchun masala tanlang.')
        if stype == 'quiz' and not test_pack:
            self.add_error('test_pack', 'Quiz session uchun test paketi tanlang.')
        if stype == 'algorithmic':
            cleaned['test_pack'] = None
        if stype == 'quiz':
            cleaned['task'] = None
        return cleaned