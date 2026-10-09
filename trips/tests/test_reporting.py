"""Reporting tests: group summary aggregation and My Trips filtering/annotation.

Expected values are calculated by hand from the data in each setUp.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from trips.models import Trip, TripMember
from trips.services.summary import group_summary

from .helpers import make_destination, make_origin, make_preference, make_trip, make_user


class GroupSummaryTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.trip = make_trip(self.owner, make_origin())
        self.members = [self.trip.members.get()] + [
            TripMember.objects.create(trip=self.trip, user=make_user(name))
            for name in ["faisal", "mohammed", "khalid"]
        ]

    def submit_three(self):
        # Khalid (4th member) hasn't submitted yet.
        make_preference(self.members[0], budget=4000, hours=5, interests=("Nature", "Food"))
        make_preference(self.members[1], budget=3000, hours=4.5, direct_only=True, interests=("Food", "Culture"))
        make_preference(self.members[2], budget=5000, hours=6, interests=("Nature", "Food", "Adventure"))

    def test_aggregates_only_submitted_preferences(self):
        self.submit_three()
        summary = group_summary(self.trip)

        self.assertEqual(summary.submitted, 3)
        self.assertEqual(summary.average_budget, 4000)       # (4000 + 3000 + 5000) / 3
        self.assertEqual(summary.lowest_budget, 3000)
        self.assertEqual(summary.shortest_flight_hours, Decimal("4.5"))
        self.assertAlmostEqual(float(summary.average_flight_hours), 5.1667, places=3)  # 15.5 / 3
        self.assertEqual(summary.direct_only_count, 1)

    def test_top_interests_counted_per_member_and_ordered(self):
        self.submit_three()
        votes = [(i.name, i.votes) for i in group_summary(self.trip).top_interests]

        # Food 3, Nature 2, then ties of 1 in alphabetical order.
        self.assertEqual(votes, [("Food", 3), ("Nature", 2), ("Adventure", 1), ("Culture", 1)])

    def test_other_trips_do_not_affect_counts(self):
        self.submit_three()
        other = make_trip(make_user("someone"), self.trip.departure_city, name="Other")
        make_preference(other.members.get(), budget=900, interests=("Food",))

        summary = group_summary(self.trip)
        self.assertEqual(summary.lowest_budget, 3000)
        self.assertEqual(dict((i.name, i.votes) for i in summary.top_interests)["Food"], 3)

    def test_empty_trip(self):
        summary = group_summary(self.trip)

        self.assertFalse(summary.has_data)
        self.assertIsNone(summary.average_budget)
        self.assertEqual(summary.top_interests, [])

    def test_budgets_hidden_below_three_submissions(self):
        make_preference(self.members[0], budget=4000)
        make_preference(self.members[1], budget=3000)

        self.assertFalse(group_summary(self.trip).shows_budgets)

    def test_trip_room_shows_summary(self):
        self.submit_three()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertContains(response, "Group summary")
        self.assertContains(response, "3,000 SAR")   # group budget limit
        self.assertContains(response, "4,000 SAR")   # average
        self.assertContains(response, "4.5 h")

    def test_trip_room_hides_budgets_for_small_groups(self):
        make_preference(self.members[0], budget=4000)
        make_preference(self.members[1], budget=3123)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertNotContains(response, "3,123")
        self.assertContains(response, "Budget figures appear once 3 members")

    def test_trip_room_empty_summary(self):
        self.client.force_login(self.owner)

        self.assertContains(self.client.get(reverse("trips:detail", args=[self.trip.pk])), "No preferences yet.")


class MyTripsReportingTests(TestCase):
    def setUp(self):
        self.ammar = make_user("ammar")
        origin = make_origin()
        self.planning = make_trip(self.ammar, origin, name="Planning trip")
        self.decided = make_trip(self.ammar, origin, name="Decided trip")
        self.cancelled = make_trip(self.ammar, origin, name="Cancelled trip")
        Trip.objects.filter(pk=self.decided.pk).update(status=Trip.Status.DECIDED, selected_destination=make_destination())
        Trip.objects.filter(pk=self.cancelled.pk).update(status=Trip.Status.CANCELLED)

        # Planning trip: 4 members, 2 of them ready.
        owner_member = self.planning.members.get()
        make_preference(owner_member, interests=("Nature", "Food", "Culture"))
        for name, ready in [("faisal", True), ("mohammed", False), ("khalid", False)]:
            member = TripMember.objects.create(trip=self.planning, user=make_user(name))
            if ready:
                make_preference(member, interests=("Food", "Shopping"))
        self.client.force_login(self.ammar)

    def names(self, query=""):
        response = self.client.get(reverse("trips:my_trips") + query)
        return [trip.name for trip in response.context["trips"]]

    def test_all_trips_newest_first(self):
        self.assertEqual(self.names(), ["Cancelled trip", "Decided trip", "Planning trip"])

    def test_filter_by_status(self):
        self.assertEqual(self.names("?status=planning"), ["Planning trip"])
        self.assertEqual(self.names("?status=decided"), ["Decided trip"])
        self.assertEqual(self.names("?status=CANCELLED"), ["Cancelled trip"])

    def test_unknown_status_shows_all(self):
        self.assertEqual(len(self.names("?status=nonsense")), 3)

    def test_status_counts(self):
        response = self.client.get(reverse("trips:my_trips"))
        counts = {f["key"]: f["count"] for f in response.context["filters"]}

        self.assertEqual(counts, {"all": 3, "planning": 1, "decided": 1, "cancelled": 1})

    def test_member_and_ready_counts_are_not_inflated(self):
        response = self.client.get(reverse("trips:my_trips") + "?status=planning")
        trip = response.context["trips"][0]

        self.assertEqual((trip.member_count, trip.ready_count), (4, 2))
        self.assertContains(response, "<strong>2 of 4</strong> ready", html=False)

    def test_filter_with_no_results_shows_empty_state(self):
        Trip.objects.filter(pk=self.cancelled.pk).update(status=Trip.Status.PLANNING)
        response = self.client.get(reverse("trips:my_trips") + "?status=cancelled")

        self.assertContains(response, "No trips here")
        self.assertContains(response, "Show all trips")
