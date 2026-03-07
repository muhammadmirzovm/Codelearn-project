from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    path('<int:pk>/', views.submission_detail, name='detail'),
]
