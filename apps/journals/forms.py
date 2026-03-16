# journals/forms.py
from django import forms
from .models import Lesson, Record


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'topic', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class RecordForm(forms.ModelForm):
    class Meta:
        model = Record
        fields = ['student', 'grade', 'attended', 'comment']