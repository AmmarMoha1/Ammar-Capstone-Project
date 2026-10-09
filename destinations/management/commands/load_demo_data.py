from django.core.management.base import BaseCommand

from destinations.catalog import load_catalog
from destinations.models import Destination, DestinationClimate, Interest, OriginCity, RouteProfile


class Command(BaseCommand):
    help = "Load the illustrative Wajha demo catalog (safe to run more than once)."

    def handle(self, *args, **options):
        load_catalog()

        self.stdout.write(self.style.SUCCESS("Demo catalog loaded:"))
        self.stdout.write(f"  Origin cities:   {OriginCity.objects.count()}")
        self.stdout.write(f"  Interests:       {Interest.objects.count()}")
        self.stdout.write(f"  Destinations:    {Destination.objects.count()}")
        self.stdout.write(f"  Routes:          {RouteProfile.objects.count()}")
        self.stdout.write(f"  Climate periods: {DestinationClimate.objects.count()}")
