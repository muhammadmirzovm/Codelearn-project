from django.urls import path
from . import views
from . import challenge_views

app_name = 'tasks'

urlpatterns = [

    path('', views.task_list, name='task_list'),
    path('create/', views.task_create, name='task_create'),
    path('<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('<int:pk>/delete/', views.task_delete, name='task_delete'),


    path('challenges/', challenge_views.challenge_list, name='challenge_list'),
    path('challenges/leaderboard/', challenge_views.leaderboard, name='leaderboard'),
    path('challenges/<int:pk>/', challenge_views.challenge_detail, name='challenge_detail'),


    path('challenges/<int:pk>/run/', challenge_views.challenge_run, name='challenge_run'),
    path('challenges/<int:pk>/submit/', challenge_views.challenge_submit, name='challenge_submit'),
]