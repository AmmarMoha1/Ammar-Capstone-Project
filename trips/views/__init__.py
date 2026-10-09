"""Views for the trips app, split by area. URLs import them from here (trips.views.<name>)."""

from .dates import availability_delete, dates, dates_apply
from .pages import credits, home
from .recommendations import (
    recommendation_detail,
    recommendations,
    recommendations_generate,
    trip_finalize,
    vote,
)
from .trips import (
    member_remove,
    my_trips,
    preferences,
    trip_cancel,
    trip_create,
    trip_detail,
    trip_edit,
    trip_join,
)

__all__ = [
    "availability_delete", "credits", "dates", "dates_apply", "home", "member_remove", "my_trips",
    "preferences", "recommendation_detail", "recommendations", "recommendations_generate",
    "trip_cancel", "trip_create", "trip_detail", "trip_edit", "trip_finalize", "trip_join", "vote",
]
