from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from trips.models import Availability, Trip, TripMember
from trips.services.dates import apply_dates, count_available, date_plan, suggest_windows
from trips.services.recommendations import generate_recommendations
from trips.services.trip_actions import TripActionError

from .helpers import make_origin, make_trip, make_user
from .test_recommendations import RecommendationTestCase

D = date  # short alias for readable ranges below


class SuggestWindowsTests(SimpleTestCase):
    """Pure function: no database. Hand-checkable examples."""

    EARLIEST = D(2027, 1, 1)

    def test_everyone_free_window_comes_first(self):
        ranges = {
            1: [(D(2027, 3, 20), D(2027, 4, 5))],
            2: [(D(2027, 3, 24), D(2027, 4, 2))],
            3: [(D(2027, 3, 27), D(2027, 4, 10))],
        }

        best = suggest_windows(ranges, 3, nights=5, earliest=self.EARLIEST)[0]

        # Everyone is free from 27 Mar to 2 Apr; the earliest 5-night trip inside is 27 Mar - 1 Apr.
        self.assertEqual((best.start, best.end, best.available), (D(2027, 3, 27), D(2027, 4, 1), 3))
        self.assertTrue(best.everyone)

    def test_partial_windows_are_ranked_after(self):
        ranges = {1: [(D(2027, 5, 1), D(2027, 5, 10))], 2: [(D(2027, 6, 1), D(2027, 6, 10))]}

        windows = suggest_windows(ranges, 2, nights=3, earliest=self.EARLIEST)

        # Nobody overlaps, so every window has 1 member free; the earliest come first.
        self.assertEqual([w.available for w in windows], [1, 1, 1])
        self.assertEqual(windows[0].start, D(2027, 5, 1))
        self.assertFalse(windows[0].everyone)

    def test_suggestions_do_not_overlap(self):
        ranges = {1: [(D(2027, 5, 1), D(2027, 5, 30))]}

        windows = suggest_windows(ranges, 1, nights=4, earliest=self.EARLIEST)

        self.assertEqual(len(windows), 3)
        for first, second in zip(windows, windows[1:]):
            self.assertLessEqual(first.end, second.start)

    def test_range_too_short_gives_nothing(self):
        ranges = {1: [(D(2027, 5, 1), D(2027, 5, 3))]}

        self.assertEqual(suggest_windows(ranges, 1, nights=4, earliest=self.EARLIEST), [])

    def test_never_suggests_before_earliest(self):
        ranges = {1: [(D(2027, 5, 1), D(2027, 5, 20))]}

        windows = suggest_windows(ranges, 1, nights=2, earliest=D(2027, 5, 10))

        self.assertTrue(all(w.start >= D(2027, 5, 10) for w in windows))

    def test_return_day_counts_as_free(self):
        ranges = {1: [(D(2027, 5, 1), D(2027, 5, 5))]}

        self.assertEqual(count_available(ranges, D(2027, 5, 1), D(2027, 5, 5)), 1)
        self.assertEqual(count_available(ranges, D(2027, 5, 1), D(2027, 5, 6)), 0)

    def test_no_ranges(self):
        self.assertEqual(suggest_windows({}, 3, nights=4, earliest=self.EARLIEST), [])


class DatesTestCase(TestCase):
    def setUp(self):
        self.ammar, self.faisal = make_user("ammar"), make_user("faisal")
        self.trip = make_trip(self.ammar, make_origin())  # starts in 30 days, 4 nights
        self.faisal_member = TripMember.objects.create(trip=self.trip, user=self.faisal)
        self.ammar_member = self.trip.members.get(user=self.ammar)
        self.today = timezone.localdate()

    def free(self, member, start_in, end_in):
        return Availability.objects.create(
            trip_member=member,
            start_date=self.today + timedelta(days=start_in),
            end_date=self.today + timedelta(days=end_in),
        )


class DatePlanTests(DatesTestCase):
    def test_plan_counts_shared_members_and_current_dates(self):
        self.free(self.ammar_member, 25, 40)

        plan = date_plan(self.trip)

        self.assertEqual((plan.shared, plan.total), (1, 2))
        self.assertEqual(plan.current.available, 1)
        self.assertEqual(plan.suggestions[0].start, self.today + timedelta(days=25))


class ApplyDatesTests(DatesTestCase):
    def test_moves_trip_keeping_its_length(self):
        new_start = self.today + timedelta(days=60)

        trip, _cleared = apply_dates(self.trip, new_start)

        self.assertEqual((trip.start_date, trip.nights), (new_start, 4))

    def test_past_start_is_rejected(self):
        with self.assertRaises(TripActionError):
            apply_dates(self.trip, self.today - timedelta(days=1))

    def test_decided_trip_cannot_move(self):
        self.trip.status = Trip.Status.CANCELLED
        self.trip.save()

        with self.assertRaises(TripActionError):
            apply_dates(self.trip, self.today + timedelta(days=60))


class ApplyDatesClearsRecommendationsTests(RecommendationTestCase):
    def test_new_dates_clear_recommendations(self):
        generate_recommendations(self.trip)

        _trip, cleared = apply_dates(self.trip, self.trip.start_date + timedelta(days=7))

        self.assertGreater(cleared, 0)
        self.assertFalse(self.trip.recommendations.exists())

    def test_same_dates_keep_recommendations(self):
        generate_recommendations(self.trip)

        apply_dates(self.trip, self.trip.start_date)

        self.assertTrue(self.trip.recommendations.exists())


class DatesViewTests(DatesTestCase):
    def url(self):
        return reverse("trips:dates", args=[self.trip.pk])

    def post_range(self, start_in, end_in):
        return self.client.post(self.url(), {
            "start_date": (self.today + timedelta(days=start_in)).isoformat(),
            "end_date": (self.today + timedelta(days=end_in)).isoformat(),
        })

    def test_member_adds_a_range(self):
        self.client.force_login(self.faisal)

        response = self.post_range(20, 40)

        self.assertRedirects(response, self.url())
        self.assertEqual(self.faisal_member.availabilities.count(), 1)

    def test_end_before_start_is_rejected(self):
        self.client.force_login(self.faisal)

        response = self.post_range(40, 20)

        self.assertContains(response, "The end date must be after the start date.")
        self.assertFalse(Availability.objects.exists())

    def test_past_and_too_long_ranges_are_rejected(self):
        self.client.force_login(self.faisal)

        self.assertContains(self.post_range(-3, 10), "The start date can&#x27;t be in the past.")
        self.assertContains(self.post_range(10, 150), "A range can be at most 90 days.")
        self.assertContains(self.post_range(300, 380), "Ranges can end at most a year from today.")
        self.assertFalse(Availability.objects.exists())

    def test_limit_of_ranges_per_member(self):
        for i in range(Availability.MAX_PER_MEMBER):
            self.free(self.faisal_member, 10 + i * 10, 15 + i * 10)
        self.client.force_login(self.faisal)

        response = self.post_range(200, 210)

        self.assertContains(response, "up to 5 date ranges")
        self.assertEqual(self.faisal_member.availabilities.count(), Availability.MAX_PER_MEMBER)

    def test_page_shows_suggestions_and_who_shared(self):
        self.free(self.ammar_member, 25, 40)
        self.free(self.faisal_member, 28, 50)
        self.client.force_login(self.faisal)

        response = self.client.get(self.url())

        self.assertContains(response, "Best dates for the group")
        self.assertContains(response, "Everyone is free")
        self.assertNotContains(response, "Use these dates")  # members can't change the dates

    def test_organizer_sees_use_these_dates(self):
        self.free(self.ammar_member, 50, 70)
        self.client.force_login(self.ammar)

        self.assertContains(self.client.get(self.url()), "Use these dates")

    def test_member_can_delete_only_own_range(self):
        mine = self.free(self.faisal_member, 20, 30)
        theirs = self.free(self.ammar_member, 20, 30)
        self.client.force_login(self.faisal)

        other = self.client.post(reverse("trips:availability_delete", args=[self.trip.pk, theirs.pk]))
        self.client.post(reverse("trips:availability_delete", args=[self.trip.pk, mine.pk]))

        self.assertEqual(other.status_code, 404)
        self.assertEqual(list(Availability.objects.all()), [theirs])

    def test_non_member_gets_404(self):
        self.client.force_login(make_user("stranger"))

        self.assertEqual(self.client.get(self.url()).status_code, 404)


class DatesApplyViewTests(DatesTestCase):
    def apply_url(self, start):
        return reverse("trips:dates_apply", args=[self.trip.pk, start.isoformat()])

    def test_organizer_confirms_then_dates_change(self):
        new_start = self.today + timedelta(days=60)
        self.client.force_login(self.ammar)

        confirm = self.client.get(self.apply_url(new_start))
        response = self.client.post(self.apply_url(new_start))

        self.assertContains(confirm, "keeping its 4 nights")
        self.assertRedirects(response, reverse("trips:detail", args=[self.trip.pk]))
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.start_date, new_start)

    def test_member_gets_403(self):
        self.client.force_login(self.faisal)

        response = self.client.post(self.apply_url(self.today + timedelta(days=60)))

        self.assertEqual(response.status_code, 403)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.start_date, self.today + timedelta(days=30))

    def test_bad_date_is_404(self):
        self.client.force_login(self.ammar)

        self.assertEqual(self.client.get(f"/trips/{self.trip.pk}/dates/use/not-a-date/").status_code, 404)
