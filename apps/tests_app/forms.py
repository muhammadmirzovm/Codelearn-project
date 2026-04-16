from django import forms
from .models import TestPack


class TestPackForm(forms.ModelForm):
    MODE_CHOICES = [
        ('session', '📋 Session uchun — o\'qituvchi sessiyada ishlatadi'),
        ('global',  '🌐 Global — har doim mavjud, coin bilan'),
    ]
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        widget=forms.RadioSelect,
        label='Test turi',
    )

    class Meta:
        model  = TestPack
        fields = ['title', 'description', 'mode', 'duration_minutes', 'coin_reward']
        widgets = {
            'description':     forms.Textarea(attrs={'rows': 2}),
            'duration_minutes': forms.NumberInput(attrs={'min': 0, 'max': 300}),
            'coin_reward':     forms.NumberInput(attrs={'min': 0, 'max': 5}),
        }
        help_texts = {
            'duration_minutes': 'Faqat Global test uchun. 0 = vaqt cheklovsiz.',
            'coin_reward':     'Faqat Global test uchun. Max 5 tanga. Faqat 100% to\'g\'ri bo\'lsa beriladi.',
        }

    def clean(self):
        cleaned = super().clean()
        mode         = cleaned.get('mode')
        coin_reward  = cleaned.get('coin_reward', 0)
        if mode == 'session':
            cleaned['duration_minutes'] = 0
            cleaned['coin_reward']      = 0
        if mode == 'global' and coin_reward > 5:
            self.add_error('coin_reward', 'Maksimal coin miqdori 5 ta.')
        return cleaned

    def clean_coin_reward(self):
        val = self.cleaned_data.get('coin_reward', 0)
        if val > 5:
            raise forms.ValidationError('Maksimal coin miqdori 5 ta.')
        return val