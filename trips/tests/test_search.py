from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from trips.models import Trip
from trips.views.trips import TRIPS_PER_PAGE

from .helpers import make_destination, make_origin, make_trip, make_user


class MyTripsSearchTests(TestCase):
    def setUp(self):
        self.ammar = make_user("ammar")
        origin = make_origin()
        self.winter = make_trip(self.ammar, origin, name="Winter Getaway")
        self.spring = make_trip(self.ammar, origin, name="Spring Break")
        self.summer = make_trip(self.ammar, origin, name="Summer Escape")
        # Summer is decided for Sarajevo, so it can be found by its destination.
        self.summer.selected_destination = make_destination(city="Sarajevo", country="Bosnia", country_code="BA")
        self.summer.status = Trip.Status.DECIDED
        self.summer.save()
        self.client.force_login(self.ammar)
        self.url = reverse("trips:my_trips")

    def tearDown(self):
        translation.activate(settings.LANGUAGE_CODE)

    def test_search_by_trip_name(self):
        response = self.client.get(self.url, {"q": "winter"})

        self.assertContains(response, "Winter Getaway")
        self.assertNotContains(response, "Spring Break")

    def test_search_by_destination(self):
        response = self.client.get(self.url, {"q": "saraj"})

        self.assertContains(response, "Summer Escape")
        self.assertNotContains(response, "Winter Getaway")

    def test_search_by_arabic_city_name(self):
        response = self.client.get("/ar" + self.url, {"q": "سراييفو"})

        self.assertContains(response, "Summer Escape")
        self.assertNotContains(response, "Winter Getaway")

    def test_tab_counts_follow_the_search(self):
        response = self.client.get(self.url, {"q": "s"})  # Spring Break, Summer Escape, Sarajevo

        counts = {f["key"]: f["count"] for f in response.context["filters"]}
        self.assertEqual(counts, {"all": 2, "planning": 1, "decided": 1, "cancelled": 0})

    def test_search_combines_with_status_filter(self):
        response = self.client.get(self.url, {"q": "s", "status": "planning"})

        self.assertContains(response, "Spring Break")
        self.assertNotContains(response, "Summer Escape")

    def test_no_results_shows_empty_state_and_is_escaped(self):
        response = self.client.get(self.url, {"q": "<b>zzz"})

        self.assertContains(response, "No trips match")
        self.assertContains(response, "&lt;b&gt;zzz")
        self.assertNotContains(response, "<b>zzz")
        self.assertContains(response, "Clear search")


class MyTripsPaginationTests(TestCase):
    def setUp(self):
        self.ammar = make_user("ammar")
        origin = make_origin()
        for number in range(TRIPS_PER_PAGE + 2):
            make_trip(self.ammar, origin, name=f"Trip {number:02d}")
        self.client.force_login(self.ammar)
        self.url = reverse("trips:my_trips")

    def test_first_page_is_full_and_newest_first(self):
        response = self.client.get(self.url)

        page = response.context["page_obj"]
        self.assertEqual(len(page.object_list), TRIPS_PER_PAGE)
        self.assertEqual(page.object_list[0].name, "Trip 10")
        self.assertContains(response, "Page 1 of 2")

    def test_second_page_has_the_rest(self):
        response = self.client.get(self.url, {"page": 2})

        self.assertEqual([t.name for t in response.context["page_obj"].object_list], ["Trip 01", "Trip 00"])

    def test_invalid_page_falls_back_safely(self):
        self.assertEqual(self.client.get(self.url, {"page": "abc"}).context["page_obj"].number, 1)
        self.assertEqual(self.client.get(self.url, {"page": 99}).context["page_obj"].number, 2)

    def test_next_link_keeps_the_filter(self):
        response = self.client.get(self.url, {"status": "planning"})

        self.assertContains(response, "?status=planning&amp;page=2")
