"""Group summary for the Trip Room.

The figures help the group see its real limits before choosing:
- the lowest budget is the most any destination can cost for everyone to go
- the shortest maximum flight is the longest flight the whole group accepts
- the most common interests show what the trip should offer
"""

from dataclasses import dataclass

from django.db.models import Avg, Count, Min, Q

from destinations.models import Interest

from ..models import Preference

# Budget figures are hidden for smaller groups: with 2 people, the lowest budget
# would reveal the other person's budget.
MIN_SUBMISSIONS_FOR_BUDGETS = 3
TOP_INTEREST_LIMIT = 5


@dataclass(frozen=True)
class GroupSummary:
    submitted: int
    average_budget: float | None
    lowest_budget: int | None
    average_flight_hours: float | None
    shortest_flight_hours: float | None
    direct_only_count: int
    top_interests: list   # Interest objects annotated with `votes`

    @property
    def has_data(self):
        return self.submitted > 0

    @property
    def shows_budgets(self):
        return self.submitted >= MIN_SUBMISSIONS_FOR_BUDGETS


def group_summary(trip):
    # Aggregation across the trip's submitted preferences (relationship: Preference -> TripMember -> Trip).
    stats = Preference.objects.filter(trip_member__trip=trip).aggregate(
        submitted=Count("id"),
        average_budget=Avg("max_budget"),
        lowest_budget=Min("max_budget"),
        average_flight_hours=Avg("max_flight_hours"),
        shortest_flight_hours=Min("max_flight_hours"),
        direct_only_count=Count("id", filter=Q(direct_only=True)),
    )

    # Annotation: each interest gets the number of this trip's members who chose it.
    top_interests = list(
        Interest.objects.annotate(
            votes=Count("preferences", filter=Q(preferences__trip_member__trip=trip))
        )
        .filter(votes__gt=0)
        .order_by("-votes", "name")[:TOP_INTEREST_LIMIT]
    )

    return GroupSummary(top_interests=top_interests, **stats)
