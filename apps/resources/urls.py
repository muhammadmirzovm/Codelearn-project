from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('',                    views.resource_home,   name='home'),
    path('websites/',           views.website_list,    name='website_list'),
    path('visit/<int:pk>/',     views.website_visit,   name='website_visit'),
    path('suggest/',            views.website_suggest, name='website_suggest'),
    path('videos/',             views.video_list,      name='video_list'),
    path('videos/add/',         views.video_add,       name='video_add'),
    path('videos/delete/<int:pk>/', views.video_delete, name='video_delete'),
]