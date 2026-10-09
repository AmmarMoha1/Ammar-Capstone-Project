import re

from django.db import IntegrityError, transaction
from django.test import TestCase

from trips.models import Trip, TripMember

from .helpers import make_destination, make_origin, make_trip, make_user


class CreateTripTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.origin = make_origin()

    def test_organizer_becomes_a_member(self):
        trip = make_trip(self.owner, self.origin)

        self.assertTrue(TripMember.objects.filter(trip=trip, user=self.owner).exists())
        self.assertEqual(trip.members.count(), 1)

    def test_new_trip_is_planning_without_destination(self):
        trip = make_trip(self.owner, self.origin)

        self.assertEqual(trip.status, Trip.Status.PLANNING)
        self.assertIsNone(trip.selected_destination)

    def test_invite_code_format(self):
        trip = make_trip(self.owner, self.origin)

        self.assertRegex(trip.invite_code, r"^WJ-[A-HJKMNP-Z2-9]{5}$")

    def test_invite_codes_are_unique(self):
        codes = {make_trip(self.owner, self.origin, name=f"Trip {i}").invite_code for i in range(20)}

        self.assertEqual(len(codes), 20)

    def test_nights(self):
        trip = make_trip(self.owner, self.origin)

        self.assertEqual(trip.nights, 4)


class TripConstraintTests(TestCase):
    def setUp(self):
        self.owner = make_user("ammar")
        self.origin = make_origin()
        self.trip = make_trip(self.owner, self.origin)
        self.destination = make_destination()

    def assert_rejected(self, change):
        with self.assertRaises(IntegrityError), transaction.atomic():
            change()

    def test_end_date_must_be_after_start_date(self):
        self.trip.end_date = self.trip.start_date
        self.assert_rejected(self.trip.save)

    def test_planning_trip_cannot_have_destination(self):
        self.trip.selected_destination = self.destination
        self.assert_rejected(self.trip.save)

    def test_decided_trip_must_have_destination(self):
        self.trip.status = Trip.Status.DECIDED
        self.assert_rejected(self.trip.save)

    def test_decided_trip_with_destination_is_valid(self):
        self.trip.status = Trip.Status.DECIDED
        self.trip.selected_destination = self.destination
        self.trip.save()

    def test_cancelled_trip_may_keep_or_have_no_destination(self):
        self.trip.status = Trip.Status.CANCELLED
        self.trip.save()

        self.trip.selected_destination = self.destination
        self.trip.save()

    def test_user_cannot_be_member_twice(self):
        self.assert_rejected(lambda: TripMember.objects.create(trip=self.trip, user=self.owner))
