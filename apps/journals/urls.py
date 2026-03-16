# apps/journals/urls.py
from django.urls import path
from . import views

app_name = 'journals'

urlpatterns = [
    path('group/<int:group_pk>/',
         views.JournalDetailView.as_view(), name='detail'),
    path('group/<int:group_pk>/lesson/add/',
         views.LessonCreateView.as_view(), name='lesson-add'),
    path('lesson/<int:lesson_pk>/records/',
         views.RecordUpdateView.as_view(), name='record-edit'),
]