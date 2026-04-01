from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps import GenericSitemap, Sitemap
from django.contrib.sitemaps.views import sitemap
from apps.tasks.models import Task


class StaticSitemap(Sitemap):
    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        return ['challenges', 'leaderboard']

    def location(self, item):
        if item == 'challenges':
            return '/en/tasks/challenges/'
        return '/en/tasks/challenges/leaderboard/'


sitemaps = {
    'static': StaticSitemap(),
    'challenges': GenericSitemap({
        'queryset': Task.objects.filter(
            scope='global', status='published'
        ),
        'date_field': 'updated_at',
    }, priority=0.8),
}

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('rosetta/', include('rosetta.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('', RedirectView.as_view(url='/en/dashboard/', permanent=False), name='home'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('users/', include('apps.users.urls', namespace='users')),
    path('dashboard/', include('apps.users.dashboard_urls', namespace='dashboard')),
    path('tasks/', include('apps.tasks.urls', namespace='tasks')),
    path('sessions/', include('apps.sessions_app.urls', namespace='sessions')),
    path('submissions/', include('apps.submissions.urls', namespace='submissions')),
    path('api/', include('apps.submissions.api_urls', namespace='api')),
    path('journals/', include('apps.journals.urls')),
    path('support/', include('apps.support.urls')),
    path('resources/', include('apps.resources.urls', namespace='resources')),
)