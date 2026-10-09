from django.urls import reverse

from trips.models import Trip, Vote
from trips.services.recommendations import generate_recommendations
from trips.services.trip_actions import TripActionError, clear_recommendations, finalize_trip
from trips.services.voting import cast_vote, vote_summary

from .helpers import make_catalog_destination
from .test_recommendations import RecommendationTestCase


class VotingTestCase(RecommendationTestCase):
    """The shared 2-member trip with four fitting destinations, so the 4th is outside the top 3."""

    def setUp(self):
        super().setUp()
        # Both fit everyone: 1200 + 400 x 4 = 2800 SAR in 2h, and 1600 + 450 x 4 = 3400 SAR in 4.5h.
        self.dubai = make_catalog_destination(self.origin, "Dubai", daily_cost=400, flight_cost=1200, hours=2,
                                              interests=("Shopping",))
        self.vienna = make_catalog_destination(self.origin, "Vienna", daily_cost=450, flight_cost=1600, hours=4.5,
                                               interests=("Culture",))
        generate_recommendations(self.trip)
        self.ammar_member = self.trip.members.get(user=self.ammar)
        self.top = list(self.trip.recommendations.order_by("rank"))

    def destination(self, rank):
        return self.top[rank - 1].destination_id


class CastVoteTests(VotingTestCase):
    def test_vote_for_a_top_three_recommendation(self):
        cast_vote(self.ammar_member, self.destination(2))

        self.assertEqual(Vote.objects.get(trip_member=self.ammar_member).recommendation.rank, 2)

    def test_changing_a_vote_keeps_one_vote(self):
        cast_vote(self.ammar_member, self.destination(1))
        cast_vote(self.ammar_member, self.destination(3))

        self.assertEqual(Vote.objects.filter(trip_member=self.ammar_member).count(), 1)
        self.assertEqual(Vote.objects.get(trip_member=self.ammar_member).recommendation.rank, 3)

    def test_fourth_place_cannot_be_voted_for(self):
        self.assertGreaterEqual(len(self.top), 4)
        with self.assertRaises(TripActionError):
            cast_vote(self.ammar_member, self.destination(4))

    def test_excluded_destination_cannot_be_voted_for(self):
        with self.assertRaises(TripActionError):
            cast_vote(self.ammar_member, self.bali.pk)

    def test_voting_closes_when_the_trip_is_decided(self):
        finalize_trip(self.trip, self.destination(1))
        self.trip.refresh_from_db()

        with self.assertRaises(TripActionError):
            cast_vote(self.trip.members.get(user=self.ammar), self.destination(1))

    def test_votes_are_cleared_with_the_recommendations(self):
        cast_vote(self.ammar_member, self.destination(1))

        clear_recommendations(self.trip)

        self.assertFalse(Vote.objects.exists())

    def test_regenerating_clears_votes(self):
        cast_vote(self.ammar_member, self.destination(1))

        generate_recommendations(self.trip)

        self.assertFalse(Vote.objects.exists())


class VoteSummaryTests(VotingTestCase):
    def test_counts_are_annotated_and_leader_found(self):
        cast_vote(self.ammar_member, self.destination(2))
        cast_vote(self.faisal_member, self.destination(2))

        summary = vote_summary(self.trip, self.ammar_member)

        self.assertEqual([o.vote_count for o in summary.options], [0, 2, 0])
        self.assertEqual(summary.voted, 2)
        self.assertEqual(summary.members, 2)
        self.assertEqual(summary.leader.rank, 2)
        self.assertEqual(summary.my_destination_id, self.destination(2))

    def test_a_tie_has_no_leader(self):
        cast_vote(self.ammar_member, self.destination(1))
        cast_vote(self.faisal_member, self.destination(2))

        self.assertIsNone(vote_summary(self.trip, self.ammar_member).leader)

    def test_no_votes_no_leader(self):
        summary = vote_summary(self.trip, self.ammar_member)

        self.assertIsNone(summary.leader)
        self.assertIsNone(summary.my_destination_id)


class VoteViewTests(VotingTestCase):
    def vote_url(self, rank):
        return reverse("trips:vote", args=[self.trip.pk, self.destination(rank)])

    def test_member_votes_from_the_recommendations_page(self):
        self.client.force_login(self.faisal)

        response = self.client.post(self.vote_url(1))

        self.assertRedirects(response, reverse("trips:recommendations", args=[self.trip.pk]) + "#vote")
        self.assertEqual(Vote.objects.get(trip_member=self.faisal_member).recommendation.rank, 1)

    def test_page_shows_totals_but_not_names(self):
        cast_vote(self.faisal_member, self.destination(1))
        self.client.force_login(self.ammar)

        response = self.client.get(reverse("trips:recommendations", args=[self.trip.pk]))

        self.assertContains(response, "<strong>1 of 2</strong> voted", html=False)
        self.assertContains(response, "1 vote")
        self.assertContains(response, "Leading")
        self.assertNotContains(response, "faisal voted")

    def test_trip_room_shows_vote_progress(self):
        cast_vote(self.faisal_member, self.destination(1))
        self.client.force_login(self.ammar)

        response = self.client.get(reverse("trips:detail", args=[self.trip.pk]))

        self.assertContains(response, "Group vote: 1 of 2 members voted.")
        self.assertContains(response, "Cast your vote")

    def test_get_does_not_vote(self):
        self.client.force_login(self.faisal)

        self.client.get(self.vote_url(1))

        self.assertFalse(Vote.objects.exists())

    def test_invalid_choice_shows_error(self):
        self.client.force_login(self.faisal)

        response = self.client.post(self.vote_url(4), follow=True)

        self.assertContains(response, "You can only vote for one of the top 3 recommendations.")
        self.assertFalse(Vote.objects.exists())

    def test_non_member_gets_404(self):
        from .helpers import make_user

        self.client.force_login(make_user("stranger"))

        self.assertEqual(self.client.post(self.vote_url(1)).status_code, 404)

    def test_decided_trip_rejects_votes(self):
        finalize_trip(self.trip, self.destination(1))
        self.client.force_login(self.faisal)

        response = self.client.post(self.vote_url(1), follow=True)

        self.assertContains(response, "Voting is closed")
        self.assertEqual(Trip.objects.get(pk=self.trip.pk).status, Trip.Status.DECIDED)
