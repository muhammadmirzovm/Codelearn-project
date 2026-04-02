from django import forms
from django.utils.translation import gettext_lazy as _
from .models import WebsiteSuggestion, Website, Video, VideoCategory


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

        if Website.objects.filter(url=url).exists():
            raise forms.ValidationError(
                _('This website is already in our list.')
            )

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


class VideoForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False,
        label=_('Or create new category'),
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Type a new category name'),
            'list': 'video-category-suggestions',
            'autocomplete': 'off',
        })
    )

    class Meta:
        model  = Video
        fields = ['title', 'url', 'description', 'language', 'category', 'new_category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Video title'),
            }),
            'url': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': _('Paste YouTube URL or <iframe> tag here'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': _('Short description (optional)'),
            }),
            'language': forms.Select(attrs={
                'class': 'form-input',
            }),
            'category': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_video_category',
            }),
        }
        labels = {
            'title':    _('Title'),
            'url':      _('YouTube URL or iframe'),
            'language': _('Language'),
            'category': _('Category'),
        }

    def clean(self):
        cleaned_data = super().clean()
        url = cleaned_data.get('url', '')
        if url and not Video.extract_youtube_id(url):
            raise forms.ValidationError(
                _('Could not find a valid YouTube video ID. Please check the URL or iframe.')
            )
        return cleaned_data