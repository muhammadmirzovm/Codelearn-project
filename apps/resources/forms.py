from django import forms
from django.utils.translation import gettext_lazy as _
from .models import WebsiteSuggestion, Website


class WebsiteSuggestionForm(forms.ModelForm):
    class Meta:
        model  = WebsiteSuggestion
        fields = ['name', 'url', 'category', 'suggested_category', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': _('e.g. MDN Web Docs'),
                'class': 'form-input',
            }),
            'url': forms.URLInput(attrs={
                'placeholder': 'https://',
                'class': 'form-input',
            }),
            'category': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_category',
            }),
            'suggested_category': forms.TextInput(attrs={
                'placeholder': _('e.g. DevOps, AI/ML, Career…'),
                'class': 'form-input',
                'id': 'id_suggested_category',
                'list': 'category-suggestions',
                'autocomplete': 'off',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': _('Why is this useful for learners?'),
                'rows': 3,
                'class': 'form-input',
            }),
        }
        labels = {
            'category':           _('Category (pick existing)'),
            'suggested_category': _('Or type / suggest a category'),
        }

    def clean_url(self):
        url = self.cleaned_data.get('url')
        if not url:
            return url

        # Already published as a website?
        if Website.objects.filter(url=url).exists():
            raise forms.ValidationError(
                _('This website is already in our list.')
            )

        # Already suggested and pending?
        qs = WebsiteSuggestion.objects.filter(
            url=url,
            status=WebsiteSuggestion.STATUS_PENDING
        )
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                _('This website has already been suggested and is awaiting review.')
            )

        return url