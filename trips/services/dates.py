"""Shared dates: find when the most members are free for a trip of the current length.

suggest_windows() and count_available() are pure functions (no database), so a
suggestion can be checked by hand and unit-tested, like the matching engine.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ..models import Availability
from .trip_actions import TripActionError, clear_recommendations


@dataclass(frozen=True)
class DateWindow:
    start: object  # date the group leaves
    end: object    # date the group returns
    available: int
    total: int

    @property
    def everyone(self):
        return self.total > 0 and self.available == self.total


@dataclass(frozen=True)
class DatePlan:
    suggestions: list   # best DateWindows, most members free first
    current: DateWindow  # the trip's current dates
    shared: int          # members who have added at least one range
    total: int


def count_available(ranges_by_member, start, end):
    """How many members have a free range that covers the whole trip, start to end."""
    return sum(
        1 for ranges in ranges_by_member.values()
        if any(free_from <= start and end <= free_until for free_from, free_until in ranges)
    )


def suggest_windows(ranges_by_member, total_members, nights, earliest, limit=3):
    """Best non-overlapping trips of `nights` nights, ranked by members free, then earliest start.

    ranges_by_member: {member_id: [(free_from, free_until), ...]}
    Every possible start day between the first free day (not before `earliest`) and the last
    one is tried; ranges are limited to a year ahead, so this is at most a few hundred checks.
    """
    all_ranges = [r for ranges in ranges_by_member.values() for r in ranges]
    if not all_ranges or nights < 1:
        return []

    day = max(earliest, min(free_from for free_from, _until in all_ranges))
    last_start = max(free_until for _from, free_until in all_ranges) - timedelta(days=nights)
    candidates = []
    while day <= last_start:
        end = day + timedelta(days=nights)
        available = count_available(ranges_by_member, day, end)
        if available:
            candidates.append(DateWindow(day, end, available, total_members))
        day += timedelta(days=1)

    candidates.sort(key=lambda window: (-window.available, window.start))
    chosen = []
    for window in candidates:
        # Skip windows that overlap one already chosen, so the suggestions are real alternatives.
        if all(window.end <= other.start or window.start >= other.end for other in chosen):
            chosen.append(window)
            if len(chosen) == limit:
                break
    return chosen


def load_ranges(trip):
    """{member_id: [(start, end), ...]} for the trip (relationship query through TripMember)."""
    ranges = defaultdict(list)
    for availability in Availability.objects.filter(trip_member__trip=trip):
        ranges[availability.trip_member_id].append((availability.start_date, availability.end_date))
    return dict(ranges)


def date_plan(trip):
    ranges = load_ranges(trip)
    total = trip.members.count()
    return DatePlan(
        suggestions=suggest_windows(ranges, total, trip.nights, timezone.localdate()),
        current=DateWindow(
            trip.start_date, trip.end_date, count_available(ranges, trip.start_date, trip.end_date), total
        ),
        shared=len(ranges),
        total=total,
    )


@transaction.atomic
def add_availability(form, membership):
    """Save a member's free range. Raises TripActionError when the trip is not planning or the member is at the limit."""
    if not membership.trip.is_planning:
        raise TripActionError(_("Dates can only be shared while the trip is being planned."))
    if membership.availabilities.count() >= Availability.MAX_PER_MEMBER:
        raise TripActionError(
            _("You can add up to %(max)d date ranges. Remove one to add another.") % {"max": Availability.MAX_PER_MEMBER}
        )
    availability = form.save(commit=False)
    availability.trip_member = membership
    availability.save()
    return availability


@transaction.atomic
def apply_dates(trip, start):
    """Move the trip to start on `start`, keeping its number of nights.

    New dates change costs and weather, so recommendations (and their votes) are cleared.
    Returns (trip, recommendations_cleared).
    """
    if not trip.is_planning:
        raise TripActionError(_("Only a trip that is still being planned can change its dates."))
    if start < timezone.localdate():
        raise TripActionError(_("The start date can't be in the past."))
    if start == trip.start_date:
        return trip, 0

    nights = trip.nights
    trip.start_date = start
    trip.end_date = start + timedelta(days=nights)
    trip.save(update_fields=["start_date", "end_date", "updated_at"])
    return trip, clear_recommendations(trip)
