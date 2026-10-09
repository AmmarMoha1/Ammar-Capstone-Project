from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from destinations.models import Interest
from trips.models import Preference, Trip, TripMember
from trips.services.recommendations import generate_recommendations

from .helpers import make_origin, make_user
from .test_recommendations import RecommendationTestCase


class FinalizeTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        generate_recommendations(self.trip)
        self.url = reverse("trips:finalize", args=[self.trip.pk, self.baku.pk])

    def test_get_shows_confirmation_without_changing_anything(self):
        self.client.force_login(self.ammar)
        response = self.client.get(self.url)

        self.assertContains(response, "Choose Baku for Winter Getaway?")
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.PLANNING)

    def test_organizer_finalizes(self):
        self.client.force_login(self.ammar)
        response = self.client.post(self.url, follow=True)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.DECIDED)
        self.assertEqual(self.trip.selected_destination, self.baku)
        self.assertContains(response, "Final destination")
        self.assertContains(response, "82%")  # stored Group Match 81.7

    def test_member_cannot_finalize(self):
        self.client.force_login(self.faisal)

        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.PLANNING)

    def test_cannot_choose_destination_that_was_not_recommended(self):
        self.client.force_login(self.ammar)
        url = reverse("trips:finalize", args=[self.trip.pk, self.bali.pk])

        self.assertEqual(self.client.post(url).status_code, 404)
        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.selected_destination)

    def test_cannot_finalize_twice(self):
        self.client.force_login(self.ammar)
        self.client.post(self.url)
        response = self.client.post(
            reverse("trips:finalize", args=[self.trip.pk, self.cairo.pk]), follow=True
        )

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.selected_destination, self.baku)
        self.assertContains(response, "Only a trip that is still being planned can be decided.")

    def test_cancelled_trip_cannot_be_finalized(self):
        self.trip.status = Trip.Status.CANCELLED
        self.trip.save()
        self.client.force_login(self.ammar)
        self.client.post(self.url)

        self.trip.refresh_from_db()
        self.assertIsNone(self.trip.selected_destination)


class DecidedTripIsLockedTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        generate_recommendations(self.trip)
        self.client.force_login(self.ammar)
        self.client.post(reverse("trips:finalize", args=[self.trip.pk, self.baku.pk]))

    def test_preferences_cannot_change(self):
        self.client.force_login(self.faisal)
        self.client.post(reverse("trips:preferences", args=[self.trip.pk]), {
            "max_budget": "9000", "max_flight_hours": "6", "weather_preference": "ANY",
            "interests": [Interest.objects.first().pk],
        })

        self.assertEqual(Preference.objects.get(trip_member=self.faisal_member).max_budget, 5000)

    def test_recommendations_are_kept_and_cannot_be_regenerated(self):
        self.client.post(reverse("trips:generate", args=[self.trip.pk]))

        self.assertEqual(self.trip.recommendations.count(), 2)

    def test_nobody_can_join(self):
        self.client.force_login(make_user("khalid"))
        self.client.post(reverse("trips:join"), {"code": self.trip.invite_code})

        self.assertEqual(self.trip.members.count(), 2)

    def test_trip_cannot_be_edited(self):
        self.client.post(reverse("trips:edit", args=[self.trip.pk]), {
            "name": "Changed", "departure_city": self.origin.pk,
            "start_date": self.trip.start_date, "end_date": self.trip.end_date,
        })

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.name, "Winter Getaway")

    def test_members_cannot_be_removed(self):
        self.client.post(reverse("trips:remove_member", args=[self.trip.pk, self.faisal_member.pk]))

        self.assertTrue(TripMember.objects.filter(pk=self.faisal_member.pk).exists())

    def test_trip_room_shows_boarding_pass_to_members(self):
        self.client.force_login(self.faisal)
        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertContains(response, "Final destination")
        self.assertContains(response, "Baku")
        self.assertNotContains(response, "Organizer actions")


class CancelTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("trips:cancel", args=[self.trip.pk])

    def test_get_shows_confirmation(self):
        self.client.force_login(self.ammar)

        self.assertContains(self.client.get(self.url), "This can&#x27;t be undone.")
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.PLANNING)

    def test_organizer_cancels_planning_trip(self):
        self.client.force_login(self.ammar)
        self.client.post(self.url)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.CANCELLED)
        self.assertTrue(Trip.objects.filter(pk=self.trip.pk).exists())  # retired, not deleted

    def test_cancelling_decided_trip_keeps_destination(self):
        generate_recommendations(self.trip)
        self.client.force_login(self.ammar)
        self.client.post(reverse("trips:finalize", args=[self.trip.pk, self.baku.pk]))
        self.client.post(self.url)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.CANCELLED)
        self.assertEqual(self.trip.selected_destination, self.baku)

    def test_member_cannot_cancel(self):
        self.client.force_login(self.faisal)

        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, Trip.Status.PLANNING)

    def test_cancelling_twice_shows_message(self):
        self.client.force_login(self.ammar)
        self.client.post(self.url)
        response = self.client.post(self.url, follow=True)

        self.assertContains(response, "This trip is already cancelled.")

    def test_cancelled_trip_stays_visible_to_members(self):
        self.client.force_login(self.ammar)
        self.client.post(self.url)
        self.client.force_login(self.faisal)

        self.assertContains(self.client.get(reverse("trips:detail", args=[self.trip.pk])), "This trip was cancelled")


class EditTripTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        generate_recommendations(self.trip)
        self.url = reverse("trips:edit", args=[self.trip.pk])
        self.client.force_login(self.ammar)

    def post(self, **overrides):
        data = {
            "name": self.trip.name,
            "departure_city": self.trip.departure_city_id,
            "start_date": self.trip.start_date.isoformat(),
            "end_date": self.trip.end_date.isoformat(),
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_form_is_prefilled(self):
        self.assertContains(self.client.get(self.url), 'value="Winter Getaway"')

    def test_renaming_keeps_recommendations(self):
        self.post(name="Baku Boys")

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.name, "Baku Boys")
        self.assertEqual(self.trip.recommendations.count(), 2)

    def test_changing_dates_clears_recommendations(self):
        self.post(end_date=(self.trip.end_date + timedelta(days=2)).isoformat())

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.nights, 6)
        self.assertFalse(self.trip.recommendations.exists())

    def test_changing_departure_city_clears_recommendations(self):
        jeddah = make_origin(code="JED", name="Jeddah")
        self.post(departure_city=jeddah.pk)

        self.assertFalse(self.trip.recommendations.exists())

    def test_end_before_start_is_rejected(self):
        response = self.post(end_date=(self.trip.start_date - timedelta(days=1)).isoformat())

        self.assertContains(response, "The end date must be after the start date.")
        self.assertEqual(self.trip.recommendations.count(), 2)

    def test_moving_start_into_past_is_rejected(self):
        response = self.post(start_date=(timezone.localdate() - timedelta(days=1)).isoformat())

        self.assertContains(response, "The start date can&#x27;t be in the past.")

    def test_member_cannot_edit(self):
        self.client.force_login(self.faisal)

        self.assertEqual(self.post(name="Hijacked").status_code, 403)


class RemoveMemberTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        generate_recommendations(self.trip)
        self.url = reverse("trips:remove_member", args=[self.trip.pk, self.faisal_member.pk])
        self.client.force_login(self.ammar)

    def test_get_shows_confirmation_without_removing(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Remove faisal from Winter Getaway?")
        self.assertTrue(TripMember.objects.filter(pk=self.faisal_member.pk).exists())

    def test_organizer_removes_member_and_dependent_records(self):
        preference_id = self.faisal_member.preference.pk
        self.client.post(self.url)

        self.assertFalse(TripMember.objects.filter(pk=self.faisal_member.pk).exists())
        self.assertFalse(Preference.objects.filter(pk=preference_id).exists())
        self.assertFalse(Preference.interests.through.objects.filter(preference_id=preference_id).exists())
        self.assertFalse(self.trip.recommendations.exists())

    def test_removed_user_loses_access(self):
        self.client.post(self.url)
        self.client.force_login(self.faisal)

        self.assertEqual(self.client.get(reverse("trips:detail", args=[self.trip.pk])).status_code, 404)

    def test_removed_user_can_rejoin(self):
        self.client.post(self.url)
        self.client.force_login(self.faisal)
        self.client.post(reverse("trips:join"), {"code": self.trip.invite_code})

        rejoined = TripMember.objects.get(trip=self.trip, user=self.faisal)
        self.assertFalse(rejoined.has_preferences)

    def test_removing_down_to_one_member_blocks_generation(self):
        self.client.post(self.url)

        self.assertFalse(self.trip.can_generate_recommendations())

    def test_removing_the_only_waiting_member_allows_generation(self):
        waiting = TripMember.objects.create(trip=self.trip, user=make_user("khalid"))
        self.assertFalse(self.trip.can_generate_recommendations())

        self.client.post(reverse("trips:remove_member", args=[self.trip.pk, waiting.pk]))

        self.assertTrue(self.trip.can_generate_recommendations())

    def test_organizer_cannot_remove_themselves(self):
        own = self.trip.members.get(user=self.ammar)
        response = self.client.post(reverse("trips:remove_member", args=[self.trip.pk, own.pk]), follow=True)

        self.assertContains(response, "The organizer can&#x27;t be removed from their own trip.")
        self.assertTrue(TripMember.objects.filter(pk=own.pk).exists())

    def test_member_cannot_remove_others(self):
        self.client.force_login(self.faisal)
        own = self.trip.members.get(user=self.ammar)

        self.assertEqual(self.client.post(reverse("trips:remove_member", args=[self.trip.pk, own.pk])).status_code, 403)

    def test_member_from_another_trip_gets_404(self):
        other_trip = Trip.objects.create(
            owner=self.ammar, departure_city=self.origin, name="Other", invite_code="WJ-OTHER",
            start_date=self.trip.start_date, end_date=self.trip.end_date,
        )
        stranger = TripMember.objects.create(trip=other_trip, user=make_user("khalid"))

        url = reverse("trips:remove_member", args=[self.trip.pk, stranger.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(TripMember.objects.filter(pk=stranger.pk).exists())

    def test_trip_room_shows_remove_only_to_organizer(self):
        detail = reverse("trips:detail", args=[self.trip.pk])

        self.assertContains(self.client.get(detail), self.url)
        self.client.force_login(self.faisal)
        self.assertNotContains(self.client.get(detail), "Remove<span")
