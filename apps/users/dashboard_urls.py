"""
Dashboard URL – dispatches to teacher or student view based on role.
"""
from django.urls import path
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.home, name='home'),
]
