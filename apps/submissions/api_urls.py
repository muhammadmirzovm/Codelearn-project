from django.urls import path
from . import api_views

app_name = 'api'

urlpatterns = [
    path('run/', api_views.run_code, name='run'),
    path('submit/', api_views.submit_code, name='submit'),
    path('status/<int:pk>/', api_views.submission_status, name='status'),
    path('leaderboard/<int:session_pk>/', api_views.leaderboard_data, name='leaderboard'),
]
