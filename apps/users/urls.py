from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),  # ← new
    path("groups/", views.group_list, name="group_list"),
    path("groups/create/", views.group_create, name="group_create"),
    path("groups/join/", views.join_group, name="join_group"),
    path("groups/<int:pk>/edit/", views.group_edit, name="group_edit"),
    path("groups/<int:pk>/delete/", views.group_delete, name="group_delete"),
    path(
        "groups/<int:pk>/regenerate-key/",
        views.group_regenerate_key,
        name="group_regenerate_key",
    ),
    path("groups/<int:group_id>/", views.group_detail, name="group_detail"),
    path("notify/<int:pk>/read/", views.mark_one_read, name="notif_mark_one"),
    path("notify/mark-read/", views.mark_all_read, name="notif_mark_read"),
    path("select-role/", views.select_role, name="select_role"),
]
