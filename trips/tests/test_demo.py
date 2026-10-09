from io import StringIO

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase

from trips.demo import DEMO_PASSWORD
from trips.models import Trip


class LoadDemoDataTests(TestCase):
    def load(self, *args):
        call_command("load_demo_data", *args, stdout=StringIO())

    def test_every_workflow_state_is_present(self):
        self.load()
        trips = {trip.name: trip for trip in Trip.objects.all()}

        self.assertEqual(len(trips), 5)
        self.assertTrue(trips["Winter Getaway"].can_generate_recommendations())
        self.assertEqual(trips["Winter Getaway"].recommendations.get(rank=1).destination.city, "Tbilisi")
        self.assertEqual(trips["Spring Break"].get_readiness().waiting, 1)
        self.assertEqual(trips["Summer Escape"].status, Trip.Status.DECIDED)
        self.assertEqual(trips["Summer Escape"].owner.username, "faisal")
        self.assertEqual(trips["Eid Trip"].status, Trip.Status.CANCELLED)
        self.assertTrue(trips["Weekend on a Budget"].can_generate_recommendations())
        self.assertFalse(trips["Weekend on a Budget"].recommendations.exists())

    def test_demo_accounts_can_log_in(self):
        self.load()

        self.assertTrue(self.client.login(username="ammar", password=DEMO_PASSWORD))

    def test_running_twice_rebuilds_without_duplicates(self):
        self.load()
        self.load()

        self.assertEqual(Trip.objects.count(), 5)
        self.assertEqual(User.objects.filter(email__endswith="@demo.wajha.test").count(), 5)

    def test_real_account_with_demo_username_is_never_touched(self):
        real = User.objects.create_user("ammar", email="me@example.com", password="my-own-password")

        with self.assertRaises(CommandError):
            self.load()

        real.refresh_from_db()
        self.assertTrue(real.check_password("my-own-password"))
        self.assertFalse(Trip.objects.exists())

    def test_catalog_only(self):
        self.load("--catalog-only")

        self.assertFalse(Trip.objects.exists())
        self.assertFalse(User.objects.exists())
