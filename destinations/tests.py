from django.db import IntegrityError, transaction
from django.test import TestCase

from .catalog import load_catalog
from .models import ClimatePeriod, Destination, DestinationClimate, Interest, OriginCity, RouteProfile


class CatalogLoaderTests(TestCase):
    def test_loads_expected_counts(self):
        load_catalog()

        self.assertEqual(OriginCity.objects.count(), 3)
        self.assertEqual(Interest.objects.count(), 7)
        self.assertEqual(Destination.objects.count(), 12)
        self.assertEqual(RouteProfile.objects.count(), 36)
        self.assertEqual(DestinationClimate.objects.count(), 48)

    def test_running_twice_does_not_duplicate(self):
        load_catalog()
        load_catalog()

        self.assertEqual(Destination.objects.count(), 12)
        self.assertEqual(RouteProfile.objects.count(), 36)
        self.assertEqual(DestinationClimate.objects.count(), 48)

    def test_route_data_depends_on_origin(self):
        load_catalog()
        baku = Destination.objects.get(city="Baku")

        from_riyadh = baku.routes.get(origin_city__airport_code="RUH")
        from_jeddah = baku.routes.get(origin_city__airport_code="JED")

        self.assertTrue(from_riyadh.direct_available)
        self.assertFalse(from_jeddah.direct_available)


class DestinationConstraintTests(TestCase):
    def setUp(self):
        self.origin = OriginCity.objects.create(name="Riyadh", airport_code="RUH")
        self.baku = Destination.objects.create(
            city="Baku", country="Azerbaijan", country_code="AZ",
            estimated_daily_cost=450, description="Test",
        )

    def assert_rejected(self, create):
        with self.assertRaises(IntegrityError), transaction.atomic():
            create()

    def test_city_country_must_be_unique(self):
        self.assert_rejected(lambda: Destination.objects.create(
            city="Baku", country="Azerbaijan", country_code="AZ",
            estimated_daily_cost=500, description="Duplicate",
        ))

    def test_daily_cost_must_be_positive(self):
        self.assert_rejected(lambda: Destination.objects.create(
            city="Nowhere", country="Test", country_code="TT",
            estimated_daily_cost=0, description="Zero cost",
        ))

    def test_one_climate_row_per_period(self):
        DestinationClimate.objects.create(
            destination=self.baku, period=ClimatePeriod.JAN_MAR, weather_type="COLD"
        )
        self.assert_rejected(lambda: DestinationClimate.objects.create(
            destination=self.baku, period=ClimatePeriod.JAN_MAR, weather_type="HOT"
        ))

    def test_one_route_per_origin_and_destination(self):
        RouteProfile.objects.create(
            origin_city=self.origin, destination=self.baku,
            flight_duration_hours=3.5, direct_available=True, estimated_flight_cost=1500,
        )
        self.assert_rejected(lambda: RouteProfile.objects.create(
            origin_city=self.origin, destination=self.baku,
            flight_duration_hours=4, direct_available=False, estimated_flight_cost=1200,
        ))

    def test_flight_duration_must_be_positive(self):
        self.assert_rejected(lambda: RouteProfile.objects.create(
            origin_city=self.origin, destination=self.baku,
            flight_duration_hours=0, direct_available=True, estimated_flight_cost=1500,
        ))


class ClimatePeriodTests(TestCase):
    def test_for_date(self):
        from datetime import date

        self.assertEqual(ClimatePeriod.for_date(date(2026, 1, 1)), ClimatePeriod.JAN_MAR)
        self.assertEqual(ClimatePeriod.for_date(date(2026, 3, 31)), ClimatePeriod.JAN_MAR)
        self.assertEqual(ClimatePeriod.for_date(date(2026, 4, 1)), ClimatePeriod.APR_JUN)
        self.assertEqual(ClimatePeriod.for_date(date(2026, 9, 30)), ClimatePeriod.JUL_SEP)
        self.assertEqual(ClimatePeriod.for_date(date(2026, 11, 20)), ClimatePeriod.OCT_DEC)
