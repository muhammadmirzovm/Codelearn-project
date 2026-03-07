"""
CodeLearn URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),
    path('users/', include('apps.users.urls', namespace='users')),
    path('dashboard/', include('apps.users.dashboard_urls', namespace='dashboard')),
    path('tasks/', include('apps.tasks.urls', namespace='tasks')),
    path('sessions/', include('apps.sessions_app.urls', namespace='sessions')),
    path('submissions/', include('apps.submissions.urls', namespace='submissions')),
    path('api/', include('apps.submissions.api_urls', namespace='api')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
