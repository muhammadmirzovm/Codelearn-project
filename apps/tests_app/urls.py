from django.urls import path
from . import views

app_name = 'tests'

urlpatterns = [
    path('',                                        views.test_list,           name='list'),
    path('create/',                                 views.test_create,         name='create'),
    path('<int:pk>/edit/',                          views.test_edit,           name='edit'),
    path('<int:pk>/delete/',                        views.test_delete,         name='delete'),
    path('<int:pk>/detail/',                        views.test_detail,         name='detail'),
    path('<int:pk>/questions/',                     views.question_manage,     name='questions'),
    # Global test routes (for students)
    path('<int:pk>/join/',                          views.global_test_join,    name='join'),
    path('<int:pk>/answer/',                        views.global_test_answer,  name='answer'),
    path('<int:pk>/finish/',                        views.global_test_finish,  name='finish'),
    path('<int:pk>/results/<int:attempt_pk>/',      views.global_test_results, name='global_results'),
]