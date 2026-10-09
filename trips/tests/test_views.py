from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from trips.models import Trip, TripMember
from trips.permissions import get_organizer_trip_or_403

from .helpers import future_dates, make_origin, make_trip, make_user


class CreateTripViewTests(TestCase):
    def setUp(self):
        self.user = make_user("ammar")
        self.origin = make_origin()
        self.client.force_login(self.user)
        self.url = reverse("trips:create")

    def post(self, **overrides):
        start, end = future_dates()
        data = {
            "name": "Winter Getaway",
            "departure_city": self.origin.pk,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_valid_trip_redirects_to_trip_room(self):
        response = self.post()

        trip = Trip.objects.get()
        self.assertRedirects(response, reverse("trips:detail", args=[trip.pk]))
        self.assertEqual(trip.owner, self.user)
        self.assertTrue(TripMember.objects.filter(trip=trip, user=self.user).exists())

    def test_missing_name_is_rejected(self):
        response = self.post(name="   ")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Trip.objects.exists())
        self.assertContains(response, "This field is required.")

    def test_end_date_before_start_is_rejected(self):
        start, _ = future_dates()
        response = self.post(end_date=(start - timedelta(days=1)).isoformat())

        self.assertFalse(Trip.objects.exists())
        self.assertContains(response, "The end date must be after the start date.")

    def test_same_start_and_end_date_is_rejected(self):
        start, _ = future_dates()
        response = self.post(end_date=start.isoformat())

        self.assertFalse(Trip.objects.exists())
        self.assertContains(response, "The end date must be after the start date.")

    def test_start_date_in_past_is_rejected(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        response = self.post(start_date=yesterday.isoformat())

        self.assertFalse(Trip.objects.exists())
        self.assertContains(response, "The start date can&#x27;t be in the past.")

    def test_inactive_departure_city_is_rejected(self):
        self.origin.is_active = False
        self.origin.save()

        self.post()

        self.assertFalse(Trip.objects.exists())

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")


class TripAccessTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.member = make_user("faisal")
        self.outsider = make_user("khalid")
        self.trip = make_trip(self.owner, make_origin())
        TripMember.objects.create(trip=self.trip, user=self.member)
        self.url = reverse("trips:detail", args=[self.trip.pk])

    def test_organizer_can_view_trip_room(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)

        self.assertContains(response, self.trip.invite_code)

    def test_member_can_view_trip_room(self):
        self.client.force_login(self.member)

        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_non_member_gets_404(self):
        self.client.force_login(self.outsider)

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_missing_trip_gets_404(self):
        self.client.force_login(self.owner)

        self.assertEqual(self.client.get(reverse("trips:detail", args=[9999])).status_code, 404)

    def test_organizer_helper_rejects_members(self):
        from django.core.exceptions import PermissionDenied

        self.assertEqual(get_organizer_trip_or_403(self.owner, self.trip.pk), self.trip)
        with self.assertRaises(PermissionDenied):
            get_organizer_trip_or_403(self.member, self.trip.pk)


class MyTripsViewTests(TestCase):
    def setUp(self):
        self.ammar = make_user("ammar")
        self.faisal = make_user("faisal")
        origin = make_origin()
        self.own_trip = make_trip(self.ammar, origin, name="Ammar's trip")
        self.joined_trip = make_trip(self.faisal, origin, name="Faisal's trip")
        self.other_trip = make_trip(self.faisal, origin, name="Private trip")
        TripMember.objects.create(trip=self.joined_trip, user=self.ammar)
        self.client.force_login(self.ammar)

    def test_shows_only_trips_user_belongs_to(self):
        response = self.client.get(reverse("trips:my_trips"))

        self.assertEqual(
            {trip.name for trip in response.context["trips"]},
            {"Ammar's trip", "Faisal's trip"},
        )

    def test_member_count_annotation(self):
        response = self.client.get(reverse("trips:my_trips"))
        counts = {trip.name: trip.member_count for trip in response.context["trips"]}

        self.assertEqual(counts, {"Ammar's trip": 1, "Faisal's trip": 2})

    def test_newest_first(self):
        response = self.client.get(reverse("trips:my_trips"))
        names = [trip.name for trip in response.context["trips"]]

        self.assertEqual(names, ["Faisal's trip", "Ammar's trip"])

    def test_empty_state(self):
        self.client.force_login(make_user("newuser"))
        response = self.client.get(reverse("trips:my_trips"))

        self.assertContains(response, "No trips yet")

    def test_home_redirects_logged_in_user(self):
        self.assertRedirects(self.client.get(reverse("trips:home")), reverse("trips:my_trips"))
