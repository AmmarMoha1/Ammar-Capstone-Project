"""Connects the database to the pure matching engine.

Loads a trip's members and candidate destinations into the engine's data
objects, saves ranked results as Recommendation rows, and builds the
plain-language reasons shown on the explanation page.
"""

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, ngettext

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
            _("Recommendations need at least 2 members, and every member must add their preferences first.")
        )

    ranked, _excluded = evaluate_trip(trip)
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

WEATHER_WORDS = {
    "COLD": gettext_lazy("cold"),
    "MILD": gettext_lazy("mild"),
    "WARM": gettext_lazy("warm"),
    "HOT": gettext_lazy("hot"),
}


def describe_exclusion(group_match):
    """Reasons a destination was excluded, as counts only (never names)."""
    reasons = []
    if count := group_match.blocked.get(OVER_BUDGET):
        reasons.append(ngettext(
            "Over budget for %(count)d member", "Over budget for %(count)d members", count
        ) % {"count": count})
    if count := group_match.blocked.get(FLIGHT_TOO_LONG):
        reasons.append(ngettext(
            "Flight too long for %(count)d member", "Flight too long for %(count)d members", count
        ) % {"count": count})
    if count := group_match.blocked.get(NO_DIRECT_FLIGHT):
        reasons.append(ngettext(
            "No direct flight (%(count)d member needs one)", "No direct flight (%(count)d members need one)", count
        ) % {"count": count})
    return reasons


def explain_group_match(group_match, trip):
    """Reasons a recommended destination fits, as (fully_met, text) pairs."""
    option = group_match.option
    matches = group_match.member_matches
    total = len(matches)
    reasons = [
        (True, _("Fits everyone's budget: about %(cost)s SAR per person") % {
            "cost": f"{group_match.estimated_cost:,}",
        }),
        (True, _("Within everyone's maximum flight time (%(hours)s hours)") % {"hours": f"{option.flight_hours:g}"}),
    ]

    if option.direct:
        reasons.append((True, _("Direct flight from %(city)s") % {"city": _(trip.departure_city.name)}))
    else:
        reasons.append((False, _("Connecting flight (no one in the group requires a direct flight)")))

    with_shared = sum(1 for m in matches if m.shared_interests)
    interest_votes = Counter(name for m in matches for name in m.shared_interests)
    if interest_votes:
        top = _(", ").join(
            f"{_(name)} ({count})" for name, count in sorted(interest_votes.items(), key=lambda i: (-i[1], i[0]))
        )
        reasons.append((with_shared == total, _("Matches interests for %(count)s of %(total)s members: %(top)s") % {
            "count": with_shared, "total": total, "top": top,
        }))
    else:
        reasons.append((False, _("Doesn't match anyone's selected interests")))

    weather_fits = sum(
        1 for m in matches if m.member.weather in (NO_WEATHER_PREFERENCE, option.weather)
    )
    reasons.append((
        weather_fits == total,
        _("Typically %(weather)s in %(month)s: suits %(count)s of %(total)s members") % {
            "weather": WEATHER_WORDS[option.weather],
            "month": date_format(trip.start_date, "F"),
            "count": weather_fits,
            "total": total,
        },
    ))
    return reasons
