from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/", views.my_trips, name="my_trips"),
    path("trips/new/", views.trip_create, name="create"),
    path("trips/join/", views.trip_join, name="join"),
    path("trips/<int:pk>/", views.trip_detail, name="detail"),
    path("trips/<int:pk>/edit/", views.trip_edit, name="edit"),
    path("trips/<int:pk>/cancel/", views.trip_cancel, name="cancel"),
    path("trips/<int:pk>/preferences/", views.preferences, name="preferences"),
    path("trips/<int:pk>/recommendations/", views.recommendations, name="recommendations"),
    path("trips/<int:pk>/recommendations/generate/", views.recommendations_generate, name="generate"),
    path(
        "trips/<int:pk>/recommendations/<int:destination_id>/",
        views.recommendation_detail,
        name="recommendation_detail",
    ),
    path("trips/<int:pk>/finalize/<int:destination_id>/", views.trip_finalize, name="finalize"),
    path("trips/<int:pk>/members/<int:member_id>/remove/", views.member_remove, name="remove_member"),
]
