from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from trips.models import Preference, Trip, TripMember

from .helpers import make_destination, make_interest, make_origin, make_preference, make_trip, make_user


class PreferenceViewTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.friend = make_user("faisal")
        self.trip = make_trip(self.owner, make_origin())
        self.friend_member = TripMember.objects.create(trip=self.trip, user=self.friend)
        self.nature = make_interest("Nature")
        self.food = make_interest("Food")
        self.url = reverse("trips:preferences", args=[self.trip.pk])
        self.client.force_login(self.friend)

    def post(self, **overrides):
        data = {
            "max_budget": "4000",
            "max_flight_hours": "5.5",
            "weather_preference": "COLD",
            "direct_only": "on",
            "interests": [self.nature.pk, self.food.pk],
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_valid_preferences_are_saved_for_own_membership(self):
        response = self.post()

        self.assertRedirects(response, reverse("trips:detail", args=[self.trip.pk]))
        preference = Preference.objects.get()
        self.assertEqual(preference.trip_member, self.friend_member)
        self.assertEqual(preference.max_budget, 4000)
        self.assertEqual(str(preference.max_flight_hours), "5.5")
        self.assertTrue(preference.direct_only)
        self.assertEqual(set(preference.interests.all()), {self.nature, self.food})

    def test_editing_updates_the_same_record(self):
        self.post()
        self.post(max_budget="2500", interests=[self.food.pk])

        preference = Preference.objects.get()
        self.assertEqual(preference.max_budget, 2500)
        self.assertEqual(list(preference.interests.all()), [self.food])

    def test_edit_form_is_prefilled(self):
        self.post()
        response = self.client.get(self.url)

        self.assertContains(response, 'value="4000"')
        self.assertContains(response, "Edit your preferences")

    def test_missing_fields_are_rejected(self):
        response = self.client.post(self.url, {})

        self.assertFalse(Preference.objects.exists())
        self.assertContains(response, "This field is required.", count=3)
        self.assertContains(response, "Choose at least one interest.")

    def test_invalid_budgets_are_rejected(self):
        for budget in ["0", "-100", "499", "100001", "abc"]:
            with self.subTest(budget=budget):
                self.post(max_budget=budget)
                self.assertFalse(Preference.objects.exists())

    def test_invalid_flight_hours_are_rejected(self):
        for hours in ["0", "0.5", "24.5", "4.3"]:
            with self.subTest(hours=hours):
                self.post(max_flight_hours=hours)
                self.assertFalse(Preference.objects.exists())

    def test_half_hour_message(self):
        response = self.post(max_flight_hours="4.3")

        self.assertContains(response, "Use whole or half hours")

    def test_non_member_gets_404(self):
        self.client.force_login(make_user("khalid"))

        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.post().status_code, 404)
        self.assertFalse(Preference.objects.exists())

    def test_cannot_change_preferences_on_cancelled_trip(self):
        self.trip.status = Trip.Status.CANCELLED
        self.trip.save()

        response = self.post()

        self.assertRedirects(response, reverse("trips:detail", args=[self.trip.pk]))
        self.assertFalse(Preference.objects.exists())

    def test_cannot_change_preferences_on_decided_trip(self):
        self.trip.status = Trip.Status.DECIDED
        self.trip.selected_destination = make_destination()
        self.trip.save()

        self.post()

        self.assertFalse(Preference.objects.exists())

    def test_same_user_can_have_different_preferences_per_trip(self):
        other_trip = make_trip(self.owner, self.trip.departure_city, name="Second trip")
        other_member = TripMember.objects.create(trip=other_trip, user=self.friend)

        self.post(max_budget="4000")
        self.client.post(reverse("trips:preferences", args=[other_trip.pk]), {
            "max_budget": "2500", "max_flight_hours": "4", "weather_preference": "ANY",
            "interests": [self.food.pk],
        })

        self.assertEqual(Preference.objects.get(trip_member=self.friend_member).max_budget, 4000)
        self.assertEqual(Preference.objects.get(trip_member=other_member).max_budget, 2500)

    def test_other_members_budget_is_not_shown_in_trip_room(self):
        self.post(max_budget="3777")
        self.client.force_login(self.owner)

        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertNotContains(response, "3777")
        self.assertNotContains(response, "3,777")

    def test_login_required(self):
        self.client.logout()

        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")


class PreferenceConstraintTests(TestCase):
    def setUp(self):
        owner = make_user("ammar")
        self.member = make_trip(owner, make_origin()).members.get()

    def test_one_preference_per_member(self):
        make_preference(self.member)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_preference(self.member)

    def test_budget_must_be_positive_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Preference.objects.create(trip_member=self.member, max_budget=0, max_flight_hours=5)


class ReadinessTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.trip = make_trip(self.owner, make_origin())
        self.owner_member = self.trip.members.get()

    def add_member(self, username, ready=False):
        member = TripMember.objects.create(trip=self.trip, user=make_user(username))
        if ready:
            make_preference(member)
        return member

    def test_counts(self):
        make_preference(self.owner_member)
        self.add_member("faisal", ready=True)
        self.add_member("mohammed")

        readiness = self.trip.get_readiness()

        self.assertEqual((readiness.total, readiness.ready, readiness.waiting), (3, 2, 1))

    def test_single_ready_member_is_not_enough(self):
        make_preference(self.owner_member)

        self.assertFalse(self.trip.can_generate_recommendations())

    def test_not_all_members_ready(self):
        make_preference(self.owner_member)
        self.add_member("faisal")

        self.assertFalse(self.trip.can_generate_recommendations())

    def test_organizer_must_also_submit(self):
        self.add_member("faisal", ready=True)

        self.assertFalse(self.trip.can_generate_recommendations())

    def test_all_members_ready(self):
        make_preference(self.owner_member)
        self.add_member("faisal", ready=True)

        self.assertTrue(self.trip.can_generate_recommendations())

    def test_cancelled_trip_cannot_generate_even_when_ready(self):
        make_preference(self.owner_member)
        self.add_member("faisal", ready=True)
        self.trip.status = Trip.Status.CANCELLED
        self.trip.save()

        self.assertFalse(self.trip.can_generate_recommendations())

    def test_trip_room_shows_readiness(self):
        make_preference(self.owner_member)
        self.add_member("faisal")
        self.client.force_login(self.owner)

        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertContains(response, "<strong>1 of 2</strong>", html=False)
        self.assertContains(response, "Waiting for 1 member")

    def test_last_missing_member_is_prompted(self):
        make_preference(self.owner_member)
        self.add_member("faisal")
        self.client.force_login(self.trip.members.get(user__username="faisal").user)

        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertContains(response, "Everyone's waiting on you")
