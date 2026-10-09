"""Connects the database to the pure matching engine.

Loads a trip's members and candidate destinations into the engine's data
objects, saves ranked results as Recommendation rows, and builds the
plain-language reasons shown on the explanation page.
"""

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from destinations.models import ClimatePeriod, RouteProfile

from ..models import Recommendation
from .matching import (
    FLIGHT_TOO_LONG,
    NO_DIRECT_FLIGHT,
    NO_WEATHER_PREFERENCE,
    OVER_BUDGET,
    DestinationOption,
    MemberPreferences,
    rank_destinations,
)
from .trip_actions import TripActionError


def load_member_preferences(trip):
    members = trip.members.select_related("user", "preference").prefetch_related("preference__interests")
    return [
        MemberPreferences(
            member_id=member.pk,
            name=member.user.username,
            max_budget=member.preference.max_budget,
            max_flight_hours=float(member.preference.max_flight_hours),
            weather=member.preference.weather_preference,
            direct_only=member.preference.direct_only,
            interests=frozenset(i.name for i in member.preference.interests.all()),
        )
        for member in members
        if member.has_preferences
    ]


def load_destination_options(trip):
    """Active destinations with a route from the trip's departure city.

    Relationship query: destinations are found through RouteProfile, filtered by the
    trip's departure city. Weather is the destination's climate for the trip's period.
    """
    period = ClimatePeriod.for_date(trip.start_date)
    routes = (
        RouteProfile.objects.filter(origin_city=trip.departure_city, destination__is_active=True)
        .select_related("destination")
        .prefetch_related("destination__interests", "destination__climates")
    )
    options = []
    for route in routes:
        destination = route.destination
        weather = next((c.weather_type for c in destination.climates.all() if c.period == period), None)
        if weather is None:
            continue  # incomplete catalog data: skip rather than guess the weather
        options.append(DestinationOption(
            destination_id=destination.pk,
            city=destination.city,
            country=destination.country,
            daily_cost=destination.estimated_daily_cost,
            flight_cost=route.estimated_flight_cost,
            flight_hours=float(route.flight_duration_hours),
            direct=route.direct_available,
            weather=weather,
            interests=frozenset(i.name for i in destination.interests.all()),
        ))
    return options


def evaluate_trip(trip):
    """Run the matching engine on the trip's current data. Returns (ranked, excluded)."""
    return rank_destinations(load_member_preferences(trip), load_destination_options(trip), trip.nights)


def _one_decimal(value):
    return Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


@transaction.atomic
def generate_recommendations(trip):
    """Replace the trip's recommendations with a fresh ranking. Returns the number saved."""
    if not trip.can_generate_recommendations():
        raise TripActionError(
            "Recommendations need at least 2 members, and every member must add their preferences first."
        )

    ranked, _ = evaluate_trip(trip)
    trip.recommendations.all().delete()
    Recommendation.objects.bulk_create(
        Recommendation(
            trip=trip,
            destination_id=match.option.destination_id,
            rank=rank,
            score=_one_decimal(match.score),
            lowest_member_score=_one_decimal(match.lowest_member_score),
            estimated_total_cost=match.estimated_cost,
        )
        for rank, match in enumerate(ranked, start=1)
    )
    return len(ranked)


# --- Plain-language explanations --------------------------------------------

def _members(count):
    return f"{count} member{'' if count == 1 else 's'}"


def describe_exclusion(group_match):
    """Reasons a destination was excluded, as counts only (never names)."""
    reasons = []
    if group_match.blocked.get(OVER_BUDGET):
        reasons.append(f"Over budget for {_members(group_match.blocked[OVER_BUDGET])}")
    if group_match.blocked.get(FLIGHT_TOO_LONG):
        reasons.append(f"Flight too long for {_members(group_match.blocked[FLIGHT_TOO_LONG])}")
    if group_match.blocked.get(NO_DIRECT_FLIGHT):
        count = group_match.blocked[NO_DIRECT_FLIGHT]
        reasons.append(f"No direct flight ({_members(count)} {'needs' if count == 1 else 'need'} one)")
    return reasons


def explain_group_match(group_match, trip):
    """Reasons a recommended destination fits, as (fully_met, text) pairs."""
    option = group_match.option
    matches = group_match.member_matches
    total = len(matches)
    reasons = [
        (True, f"Fits everyone's budget: about {group_match.estimated_cost:,} SAR per person"),
        (True, f"Within everyone's maximum flight time ({option.flight_hours:g} hours)"),
    ]

    if option.direct:
        reasons.append((True, f"Direct flight from {trip.departure_city.name}"))
    else:
        reasons.append((False, "Connecting flight (no one in the group requires a direct flight)"))

    with_shared = sum(1 for m in matches if m.shared_interests)
    interest_votes = Counter(name for m in matches for name in m.shared_interests)
    if interest_votes:
        top = ", ".join(f"{name} ({count})" for name, count in sorted(interest_votes.items(), key=lambda i: (-i[1], i[0])))
        reasons.append((with_shared == total, f"Matches interests for {with_shared} of {total} members: {top}"))
    else:
        reasons.append((False, "Doesn't match anyone's selected interests"))

    weather_fits = sum(
        1 for m in matches if m.member.weather in (NO_WEATHER_PREFERENCE, option.weather)
    )
    month = trip.start_date.strftime("%B")
    reasons.append((
        weather_fits == total,
        f"Typically {option.weather.lower()} in {month}: suits {weather_fits} of {total} members",
    ))
    return reasons
