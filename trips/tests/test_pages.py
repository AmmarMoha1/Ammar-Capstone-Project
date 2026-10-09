from django.test import TestCase
from django.urls import reverse

from trips.models import TripMember

from .helpers import make_origin, make_trip, make_user


class ErrorPageTests(TestCase):
    def test_custom_404_page(self):
        self.client.force_login(make_user("ammar"))
        response = self.client.get("/trips/9999/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "We couldn't find that page", status_code=404)
        self.assertContains(response, "Join a trip with a code", status_code=404)

    def test_custom_403_page(self):
        owner, member = make_user("ammar"), make_user("faisal")
        trip = make_trip(owner, make_origin())
        TripMember.objects.create(trip=trip, user=member)
        self.client.force_login(member)

        response = self.client.get(reverse("trips:edit", args=[trip.pk]))

        self.assertContains(response, "Only the organizer can do that", status_code=403)


class PublicPageTests(TestCase):
    def test_landing_page(self):
        response = self.client.get(reverse("trips:home"))

        self.assertContains(response, "Wajha finds the destination everyone can agree on")
        self.assertContains(response, "Top pick · example")

    def test_credits_page_lists_photos_and_font(self):
        from destinations.photos import PHOTOS

        response = self.client.get(reverse("trips:credits"))

        for city, photo in PHOTOS.items():
            self.assertContains(response, photo["artist"])
        self.assertContains(response, "SIL Open Font License")

    def test_footer_links_to_credits(self):
        self.assertContains(self.client.get(reverse("trips:home")), reverse("trips:credits"))
