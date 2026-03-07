from django import forms
from .models import Session

INPUT_CSS = 'w-full bg-[#1a1f2e] border border-[#2d3548] rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition'


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ('group', 'task', 'start_time', 'duration_minutes')
        widgets = {
            'group': forms.Select(attrs={'class': INPUT_CSS}),
            'task': forms.Select(attrs={'class': INPUT_CSS}),
            'start_time': forms.DateTimeInput(
                attrs={'class': INPUT_CSS, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'duration_minutes': forms.NumberInput(attrs={
                'class': INPUT_CSS, 'min': 0, 'max': 300,
                'placeholder': '0 = no limit'
            }),
        }

    def __init__(self, teacher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.users.models import Group
        from apps.tasks.models import Task
        self.fields['group'].queryset = Group.objects.filter(teacher=teacher)
        self.fields['task'].queryset = Task.objects.filter(created_by=teacher)
        self.fields['duration_minutes'].help_text = 'Minutes students have to solve. 0 = unlimited.'
