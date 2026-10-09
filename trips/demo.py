"""Fictitious demo accounts and trips covering every state of the workflow.

All names, emails and preferences are invented. Trips use fixed 2027 dates so
recommendation scores stay the same every time the demo is loaded.
Demo trips are rebuilt on every run; non-demo accounts are never touched.
"""

from datetime import date

from django.contrib.auth.models import User
from django.db import transaction

from destinations.models import Interest, OriginCity

from .models import Availability, Preference, Trip
from .services.recommendations import generate_recommendations
from .services.trip_actions import cancel_trip, create_trip, finalize_trip, join_trip
from .services.voting import cast_vote

DEMO_PASSWORD = "wajha-demo-2026"
DEMO_EMAIL_DOMAIN = "demo.wajha.test"
DEMO_USERS = ["ammar", "faisal", "mohammed", "khalid", "sara"]

# (budget SAR, max flight hours, weather, direct only, interests)
WINTER_PREFERENCES = {
    "ammar": (4500, 6, "COLD", False, ["Nature", "Food"]),
    "faisal": (4000, 5, "MILD", True, ["Food", "Culture"]),
    "mohammed": (5000, 6, "ANY", False, ["Nature", "Adventure"]),
    "khalid": (3800, 7, "COLD", False, ["Shopping", "Food"]),
}
SPRING_PREFERENCES = {
    "ammar": (6000, 8, "WARM", False, ["Beaches", "Food"]),
    "sara": (5500, 7, "WARM", False, ["Shopping", "Culture"]),
    # khalid has joined but not submitted yet
}
SUMMER_PREFERENCES = {
    "faisal": (7000, 6, "WARM", False, ["Nature", "Adventure"]),
    "ammar": (6500, 7, "WARM", False, ["Nature", "Food"]),
    "mohammed": (8000, 8, "MILD", False, ["Adventure", "Nature"]),
    "sara": (6000, 6, "ANY", True, ["Nature", "Culture"]),
}
EID_PREFERENCES = {
    "ammar": (5000, 6, "ANY", False, ["Food"]),
}
# Free date ranges (both days included). Spring Break's current dates (25-30 Mar) don't suit
# khalid; the shared-dates page suggests 27 Mar - 1 Apr, when all three are free.
SPRING_AVAILABILITY = {
    "ammar": [(date(2027, 3, 20), date(2027, 4, 5))],
    "sara": [(date(2027, 3, 24), date(2027, 4, 2))],
    "khalid": [(date(2027, 3, 27), date(2027, 4, 10))],
}
WINTER_AVAILABILITY = {
    "ammar": [(date(2027, 1, 10), date(2027, 1, 25))],
    "faisal": [(date(2027, 1, 12), date(2027, 1, 20))],
    "mohammed": [(date(2027, 1, 14), date(2027, 1, 31))],
}
# Winter Getaway votes among the top 3 (ammar hasn't voted yet, so the demo can show voting).
WINTER_VOTES = {"faisal": "Tbilisi", "khalid": "Tbilisi", "mohammed": "Sarajevo"}

BUDGET_PREFERENCES = {
    "ammar": (1500, 3, "ANY", True, ["Food"]),
    "khalid": (1800, 2, "ANY", True, ["Shopping"]),
}


class DemoDataError(Exception):
    pass


def _demo_users():
    users = {}
    for username in DEMO_USERS:
        email = f"{username}@{DEMO_EMAIL_DOMAIN}"
        user = User.objects.filter(username=username).first()
        if user and user.email != email:
            raise DemoDataError(
                f"A non-demo account named '{username}' already exists. "
                "Demo data was not loaded, so that account was left untouched."
            )
        if user is None:
            user = User(username=username, email=email)
        user.first_name = username.capitalize()
        user.set_password(DEMO_PASSWORD)
        user.save()
        users[username] = user
    return users


def _add_trip(users, owner, name, origin_code, start, end, members, preferences):
    trip = create_trip(
        users[owner],
        name=name,
        departure_city=OriginCity.objects.get(airport_code=origin_code),
        start_date=start,
        end_date=end,
    )
    for username in members:
        join_trip(users[username], trip.invite_code)
    for username, (budget, hours, weather, direct_only, interests) in preferences.items():
        preference = Preference.objects.create(
            trip_member=trip.members.get(user=users[username]),
            max_budget=budget,
            max_flight_hours=hours,
            weather_preference=weather,
            direct_only=direct_only,
        )
        preference.interests.set(Interest.objects.filter(name__in=interests))
    return trip


def _add_availability(trip, users, availability):
    for username, ranges in availability.items():
        member = trip.members.get(user=users[username])
        for start, end in ranges:
            Availability.objects.create(trip_member=member, start_date=start, end_date=end)


def _add_votes(trip, users, votes):
    for username, city in votes.items():
        recommendation = trip.recommendations.get(destination__city=city)
        cast_vote(trip.members.get(user=users[username]), recommendation.destination_id)


@transaction.atomic
def load_demo_trips():
    """Rebuild the demo trips. Returns the created trips by name."""
    users = _demo_users()
    # Start clean: remove every trip owned by a demo account (members, preferences
    # and recommendations are removed with them by CASCADE).
    Trip.objects.filter(owner__email__endswith=f"@{DEMO_EMAIL_DOMAIN}").delete()

    # Created oldest first, so "Winter Getaway" is the newest and appears first in My Trips.
    budget = _add_trip(users, "ammar", "Weekend on a Budget", "RUH", date(2027, 2, 4), date(2027, 2, 7),
                       ["khalid"], BUDGET_PREFERENCES)

    eid = _add_trip(users, "ammar", "Eid Trip", "RUH", date(2027, 3, 8), date(2027, 3, 12),
                    ["faisal"], EID_PREFERENCES)
    cancel_trip(eid)

    summer = _add_trip(users, "faisal", "Summer Escape", "RUH", date(2027, 7, 8), date(2027, 7, 14),
                       ["ammar", "mohammed", "sara"], SUMMER_PREFERENCES)
    generate_recommendations(summer)
    summer = finalize_trip(summer, summer.recommendations.get(rank=1).destination_id)

    spring = _add_trip(users, "ammar", "Spring Break", "JED", date(2027, 3, 25), date(2027, 3, 30),
                       ["sara", "khalid"], SPRING_PREFERENCES)
    _add_availability(spring, users, SPRING_AVAILABILITY)

    winter = _add_trip(users, "ammar", "Winter Getaway", "RUH", date(2027, 1, 14), date(2027, 1, 18),
                       ["faisal", "mohammed", "khalid"], WINTER_PREFERENCES)
    generate_recommendations(winter)
    _add_availability(winter, users, WINTER_AVAILABILITY)
    _add_votes(winter, users, WINTER_VOTES)

    return {trip.name: trip for trip in (budget, eid, summer, spring, winter)}
