from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Group

from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm

CSS = 'inp'


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({'class': CSS})


class GroupForm(forms.ModelForm):
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.STUDENT),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Group
        fields = ('name', 'students')
        widgets = {
            'name': forms.TextInput(attrs={'class': CSS, 'placeholder': 'e.g. Morning Python Class'}),
        }


# ── Add these imports at the top of forms.py ──────────────────────────────
class ProfileForm(forms.ModelForm):
    """Edit basic profile info."""
    first_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
    )

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email']


class PasswordChangeForm(DjangoPasswordChangeForm):
    """Thin wrapper — just customise placeholders."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs['placeholder'] = 'Current password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm new password'
        # Remove Django's default help text on the password fields
        self.fields['new_password1'].help_text = ''