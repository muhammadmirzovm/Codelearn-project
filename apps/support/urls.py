from django.urls import path
from . import views

app_name = "support"

urlpatterns = [
    path("contact/", views.contact, name="contact"),
    path("my-tickets/", views.my_tickets, name="my_tickets"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/", views.ticket_detail, name="ticket_detail"),
]
