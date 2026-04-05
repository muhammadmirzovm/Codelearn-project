# apps/journals/urls.py
from django.urls import path
from . import views

app_name = 'journals'

urlpatterns = [
    path('group/<int:group_pk>/',
         views.JournalDetailView.as_view(), name='detail'),

    # Lesson CRUD
    path('group/<int:group_pk>/lesson/add/',
         views.LessonCreateView.as_view(), name='lesson-add'),
    path('lesson/<int:lesson_pk>/edit/',
         views.LessonUpdateView.as_view(), name='lesson-edit'),
    path('lesson/<int:lesson_pk>/delete/',
         views.LessonDeleteView.as_view(), name='lesson-delete'),

    # Records (grading)
    path('lesson/<int:lesson_pk>/records/',
         views.RecordUpdateView.as_view(), name='record-edit'),

    # Membership join-date editor
    path('membership/<int:membership_pk>/update/',
         views.MembershipUpdateView.as_view(), name='membership-update'),
]