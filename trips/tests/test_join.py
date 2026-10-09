from django.test import TestCase
from django.urls import reverse

from trips.forms import JoinTripForm
from trips.models import Trip, TripMember

from .helpers import make_destination, make_origin, make_trip, make_user


class JoinTripFormTests(TestCase):
    def clean(self, code):
        form = JoinTripForm({"code": code})
        return form.cleaned_data["code"] if form.is_valid() else None

    def test_normalises_common_typing_variations(self):
        for typed in ["WJ-8K32L", "wj-8k32l", "  WJ 8K32L ", "WJ8K32L", "8K32L", "8k32l"]:
            with self.subTest(typed=typed):
                self.assertEqual(self.clean(typed), "WJ-8K32L")

    def test_code_whose_own_part_starts_with_wj(self):
        self.assertEqual(self.clean("WJ3K2"), "WJ-WJ3K2")
        self.assertEqual(self.clean("WJ-WJ3K2"), "WJ-WJ3K2")

    def test_rejects_badly_formed_codes(self):
        # Too short, too long, and ambiguous characters that codes never contain.
        for typed in ["WJ-8K3", "WJ-8K32LL", "WJ-0O1IL", "hello"]:
            with self.subTest(typed=typed):
                self.assertIsNone(self.clean(typed))


class JoinTripViewTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.friend = make_user("faisal")
        self.trip = make_trip(self.owner, make_origin())
        self.url = reverse("trips:join")
        self.client.force_login(self.friend)

    def join(self, code=None):
        return self.client.post(self.url, {"code": code or self.trip.invite_code})

    def test_valid_code_joins_and_redirects_to_trip_room(self):
        response = self.join()

        self.assertRedirects(response, reverse("trips:detail", args=[self.trip.pk]))
        self.assertTrue(TripMember.objects.filter(trip=self.trip, user=self.friend).exists())

    def test_lowercase_code_without_prefix_works(self):
        self.join(self.trip.invite_code[3:].lower())

        self.assertTrue(TripMember.objects.filter(trip=self.trip, user=self.friend).exists())

    def test_joined_trip_appears_in_my_trips(self):
        self.join()
        response = self.client.get(reverse("trips:my_trips"))

        self.assertContains(response, self.trip.name)

    def test_unknown_code_shows_error(self):
        response = self.join("WJ-ZZZZZ")

        self.assertContains(response, "No trip uses that code.")
        self.assertEqual(self.trip.members.count(), 1)

    def test_badly_formed_code_shows_error(self):
        response = self.join("hello")

        self.assertContains(response, "doesn&#x27;t look like a Wajha code")

    def test_joining_twice_does_not_duplicate(self):
        self.join()
        response = self.join()

        self.assertRedirects(response, reverse("trips:detail", args=[self.trip.pk]))
        self.assertEqual(TripMember.objects.filter(trip=self.trip, user=self.friend).count(), 1)

    def test_organizer_joining_own_trip_does_not_duplicate(self):
        self.client.force_login(self.owner)
        self.join()

        self.assertEqual(self.trip.members.count(), 1)

    def test_cancelled_trip_cannot_be_joined(self):
        self.trip.status = Trip.Status.CANCELLED
        self.trip.save()

        response = self.join()

        self.assertContains(response, "This trip is cancelled and no longer accepts new members.")
        self.assertFalse(TripMember.objects.filter(trip=self.trip, user=self.friend).exists())

    def test_decided_trip_cannot_be_joined(self):
        self.trip.status = Trip.Status.DECIDED
        self.trip.selected_destination = make_destination()
        self.trip.save()

        response = self.join()

        self.assertContains(response, "This trip is decided and no longer accepts new members.")

    def test_full_trip_cannot_be_joined(self):
        for i in range(Trip.MAX_MEMBERS - 1):
            TripMember.objects.create(trip=self.trip, user=make_user(f"member{i}"))

        response = self.join()

        self.assertContains(response, "This trip is full.")
        self.assertEqual(self.trip.members.count(), Trip.MAX_MEMBERS)

    def test_last_free_place_can_be_taken(self):
        for i in range(Trip.MAX_MEMBERS - 2):
            TripMember.objects.create(trip=self.trip, user=make_user(f"member{i}"))

        self.join()

        self.assertEqual(self.trip.members.count(), Trip.MAX_MEMBERS)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
