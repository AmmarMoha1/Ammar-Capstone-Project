from decimal import Decimal

from django.db import transaction

from .catalog_data import DESTINATIONS, INTERESTS, ORIGIN_CITIES
from .models import ClimatePeriod, Destination, DestinationClimate, Interest, OriginCity, RouteProfile


@transaction.atomic
def load_catalog():
    """Create or update the demo catalog. Safe to run more than once."""
    origins = {}
    for name, code in ORIGIN_CITIES:
        origins[code], _ = OriginCity.objects.update_or_create(
            airport_code=code, defaults={"name": name, "is_active": True}
        )

    interests = {
        name: Interest.objects.get_or_create(name=name)[0] for name in INTERESTS
    }

    for item in DESTINATIONS:
        destination, _ = Destination.objects.update_or_create(
            city=item["city"],
            country=item["country"],
            defaults={
                "country_code": item["country_code"],
                "estimated_daily_cost": item["daily_cost"],
                "description": item["description"],
                "is_active": True,
            },
        )
        destination.interests.set(interests[name] for name in item["interests"])

        for period, weather in zip(ClimatePeriod.values, item["climate"]):
            DestinationClimate.objects.update_or_create(
                destination=destination, period=period, defaults={"weather_type": weather}
            )

        for code, (hours, direct, fare) in item["routes"].items():
            RouteProfile.objects.update_or_create(
                origin_city=origins[code],
                destination=destination,
                defaults={
                    "flight_duration_hours": Decimal(str(hours)),
                    "direct_available": direct,
                    "estimated_flight_cost": fare,
                },
            )
