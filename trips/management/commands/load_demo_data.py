from django.core.management.base import BaseCommand, CommandError

from destinations.catalog import load_catalog
from destinations.models import Destination, DestinationClimate, Interest, OriginCity, RouteProfile
from trips.demo import DEMO_PASSWORD, DEMO_USERS, DemoDataError, load_demo_trips


class Command(BaseCommand):
    help = "Load the illustrative catalog plus fictitious demo accounts and trips (safe to run again)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog-only", action="store_true", help="Load destinations only, without demo accounts or trips."
        )

    def handle(self, *args, **options):
        load_catalog()
        self.stdout.write(self.style.SUCCESS("Catalog loaded:"))
        self.stdout.write(f"  Origin cities:   {OriginCity.objects.count()}")
        self.stdout.write(f"  Interests:       {Interest.objects.count()}")
        self.stdout.write(f"  Destinations:    {Destination.objects.count()}")
        self.stdout.write(f"  Routes:          {RouteProfile.objects.count()}")
        self.stdout.write(f"  Climate periods: {DestinationClimate.objects.count()}")

        if options["catalog_only"]:
            return

        try:
            trips = load_demo_trips()
        except DemoDataError as error:
            raise CommandError(str(error))

        self.stdout.write(self.style.SUCCESS("\nDemo trips loaded:"))
        for name, trip in trips.items():
            self.stdout.write(f"  {name:<22} {trip.get_status_display():<10} organizer: {trip.owner.username}")
        self.stdout.write(self.style.SUCCESS("\nDemo accounts (fictitious): ") + ", ".join(DEMO_USERS))
        self.stdout.write(f"Password for every demo account: {DEMO_PASSWORD}")
