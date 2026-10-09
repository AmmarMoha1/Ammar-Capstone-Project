from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Trip


def get_member_trip_or_404(user, pk):
    """Return the trip only if `user` is a member of it.

    Non-members get a 404 rather than a 403 so the trip's existence is not revealed.
    """
    trips = Trip.objects.select_related("owner", "departure_city", "selected_destination")
    return get_object_or_404(trips.filter(members__user=user), pk=pk)


def get_organizer_trip_or_403(user, pk):
    """Return the trip only if `user` is its organizer (403 for other members)."""
    trip = get_member_trip_or_404(user, pk)
    if not trip.is_organizer(user):
        raise PermissionDenied("Only the trip organizer can do this.")
    return trip
