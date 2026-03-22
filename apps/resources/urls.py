from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('',              views.website_list,   name='website_list'),
    path('visit/<int:pk>/', views.website_visit, name='website_visit'),
    path('suggest/',      views.website_suggest, name='website_suggest'),
]