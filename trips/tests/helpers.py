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
