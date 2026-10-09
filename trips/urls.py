from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/", views.my_trips, name="my_trips"),
    path("trips/new/", views.trip_create, name="create"),
    path("trips/<int:pk>/", views.trip_detail, name="detail"),
]
