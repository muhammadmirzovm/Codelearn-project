from django.urls import path
from . import views

app_name = 'sessions'

urlpatterns = [
    path('',                          views.session_list,     name='session_list'),
    path('create/',                   views.session_create,   name='session_create'),
    path('<int:pk>/activate/',        views.session_activate, name='activate'),
    path('<int:pk>/deactivate/',      views.session_deactivate, name='deactivate'),
    path('<int:pk>/monitor/',         views.session_monitor,  name='monitor'),
    path('<int:pk>/join/',            views.session_join,     name='join'),
    path('<int:pk>/quiz/answer/',     views.quiz_answer,      name='quiz_answer'),
    path('<int:pk>/quiz/finish/',     views.quiz_finish,      name='quiz_finish'),
    path('<int:pk>/quiz/results/',    views.quiz_results,     name='quiz_results'),
    path('<int:pk>/leaderboard/',     views.leaderboard,      name='leaderboard'),
]