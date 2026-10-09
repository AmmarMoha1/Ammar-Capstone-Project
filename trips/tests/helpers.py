from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from destinations.models import Destination, OriginCity
from trips.services.trip_actions import create_trip


def make_user(username):
    return User.objects.create_user(username=username, password="test-pass-123")


def make_origin(code="RUH", name="Riyadh"):
    return OriginCity.objects.create(name=name, airport_code=code)


def make_destination(city="Baku", country="Azerbaijan", country_code="AZ", daily_cost=450):
    return Destination.objects.create(
        city=city, country=country, country_code=country_code,
        estimated_daily_cost=daily_cost, description="Test destination",
    )


def future_dates(start_in_days=30, nights=4):
    start = timezone.localdate() + timedelta(days=start_in_days)
    return start, start + timedelta(days=nights)


def make_trip(owner, origin, name="Winter Getaway"):
    start, end = future_dates()
    return create_trip(owner, name=name, departure_city=origin, start_date=start, end_date=end)


def make_interest(name="Nature"):
    from destinations.models import Interest

    return Interest.objects.get_or_create(name=name)[0]


def make_preference(member, budget=4000, hours=5, weather="ANY", direct_only=False, interests=("Nature",)):
    from trips.models import Preference

    preference = Preference.objects.create(
        trip_member=member, max_budget=budget, max_flight_hours=hours,
        weather_preference=weather, direct_only=direct_only,
    )
    preference.interests.set(make_interest(name) for name in interests)
    return preference
