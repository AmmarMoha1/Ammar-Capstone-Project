from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from trips.models import Recommendation, Trip, TripMember
from trips.services.recommendations import evaluate_trip, generate_recommendations
from trips.services.trip_actions import TripActionError

from .helpers import (
    make_catalog_destination,
    make_destination,
    make_interest,
    make_origin,
    make_preference,
    make_trip,
    make_user,
)


class RecommendationTestCase(TestCase):
    """A 2-member trip (4 nights from RUH) with three candidate destinations.

    Ammar: budget 4000, max 5h, Cold, interests Nature + Food
    Faisal: budget 5000, max 6h, Mild, direct only, interests Culture + Food
    """

    def setUp(self):
        self.origin = make_origin()
        self.ammar = make_user("ammar")
        self.faisal = make_user("faisal")
        self.trip = make_trip(self.ammar, self.origin)
        self.faisal_member = TripMember.objects.create(trip=self.trip, user=self.faisal)
        make_preference(self.trip.members.get(user=self.ammar), budget=4000, hours=5,
                        weather="COLD", interests=("Nature", "Food"))
        make_preference(self.faisal_member, budget=5000, hours=6, weather="MILD",
                        direct_only=True, interests=("Culture", "Food"))

        # Fits both: cost 1500 + 450 x 4 = 3300.
        self.baku = make_catalog_destination(self.origin, "Baku", interests=("Culture", "Food", "Nightlife"))
        # Fits both, cheaper and shorter: cost 1100 + 350 x 4 = 2500.
        self.cairo = make_catalog_destination(self.origin, "Cairo", daily_cost=350, flight_cost=1100,
                                              hours=2.5, weather="MILD", interests=("Culture", "Food"))
        # Over Ammar's budget (4200 + 600 x 4 = 6600) and not direct for Faisal.
        self.bali = make_catalog_destination(self.origin, "Bali", daily_cost=600, flight_cost=4200,
                                             hours=13, direct=False, weather="HOT", interests=("Beaches",))


class GenerateServiceTests(RecommendationTestCase):
    def test_saves_ranked_destinations_that_fit_everyone(self):
        count = generate_recommendations(self.trip)

        recs = list(self.trip.recommendations.order_by("rank"))
        self.assertEqual(count, 2)
        self.assertEqual([r.rank for r in recs], [1, 2])
        self.assertNotIn(self.bali, [r.destination for r in recs])
        self.assertGreaterEqual(recs[0].score, recs[1].score)

    def test_saved_values_match_the_engine(self):
        generate_recommendations(self.trip)
        ranked, _ = evaluate_trip(self.trip)

        for rec, match in zip(self.trip.recommendations.order_by("rank"), ranked):
            self.assertEqual(rec.destination_id, match.option.destination_id)
            self.assertEqual(rec.score, Decimal(str(round(match.score, 1))))
            self.assertEqual(rec.estimated_total_cost, match.estimated_cost)

    def test_baku_score_matches_hand_calculation(self):
        # Same numbers as the matching tests: 0.7 x 83.34375 + 0.3 x 77.9375 = 81.72 -> 81.7
        generate_recommendations(self.trip)

        baku = self.trip.recommendations.get(destination=self.baku)
        self.assertEqual(baku.score, Decimal("81.7"))
        self.assertEqual(baku.lowest_member_score, Decimal("77.9"))
        self.assertEqual(baku.estimated_total_cost, 3300)

    def test_regenerating_replaces_rows(self):
        generate_recommendations(self.trip)
        generate_recommendations(self.trip)

        self.assertEqual(self.trip.recommendations.count(), 2)

    def test_refuses_when_not_ready(self):
        TripMember.objects.create(trip=self.trip, user=make_user("khalid"))

        with self.assertRaises(TripActionError):
            generate_recommendations(self.trip)
        self.assertFalse(Recommendation.objects.exists())

    def test_inactive_destination_is_ignored(self):
        self.cairo.is_active = False
        self.cairo.save()

        generate_recommendations(self.trip)

        self.assertEqual(list(self.trip.recommendations.values_list("destination__city", flat=True)), ["Baku"])

    def test_nothing_fits(self):
        Recommendation.objects.all().delete()
        self.baku.delete()
        self.cairo.delete()

        self.assertEqual(generate_recommendations(self.trip), 0)


class RecommendationConstraintTests(RecommendationTestCase):
    def test_rank_unique_per_trip(self):
        Recommendation.objects.create(trip=self.trip, destination=self.baku, rank=1, score=80,
                                      lowest_member_score=70, estimated_total_cost=3300)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Recommendation.objects.create(trip=self.trip, destination=self.cairo, rank=1, score=70,
                                          lowest_member_score=60, estimated_total_cost=2500)

    def test_score_must_be_within_range(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Recommendation.objects.create(trip=self.trip, destination=self.baku, rank=1, score=101,
                                          lowest_member_score=70, estimated_total_cost=3300)


class GenerateViewTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("trips:generate", args=[self.trip.pk])

    def test_organizer_generates(self):
        self.client.force_login(self.ammar)
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse("trips:recommendations", args=[self.trip.pk]))
        self.assertEqual(self.trip.recommendations.count(), 2)

    def test_member_cannot_generate(self):
        self.client.force_login(self.faisal)

        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertFalse(Recommendation.objects.exists())

    def test_non_member_gets_404(self):
        self.client.force_login(make_user("khalid"))

        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_get_does_not_generate(self):
        self.client.force_login(self.ammar)
        self.client.get(self.url)

        self.assertFalse(Recommendation.objects.exists())

    def test_not_ready_shows_error(self):
        TripMember.objects.create(trip=self.trip, user=make_user("khalid"))
        self.client.force_login(self.ammar)

        response = self.client.post(self.url, follow=True)

        self.assertContains(response, "every member must add their preferences first")
        self.assertFalse(Recommendation.objects.exists())


class InvalidationTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        generate_recommendations(self.trip)

    def test_saving_preferences_clears_recommendations(self):
        self.client.force_login(self.faisal)
        self.client.post(reverse("trips:preferences", args=[self.trip.pk]), {
            "max_budget": "6000", "max_flight_hours": "6", "weather_preference": "MILD",
            "direct_only": "on", "interests": [make_interest("Food").pk],
        })

        self.assertFalse(self.trip.recommendations.exists())

    def test_invalid_preferences_do_not_clear(self):
        self.client.force_login(self.faisal)
        self.client.post(reverse("trips:preferences", args=[self.trip.pk]), {"max_budget": "0"})

        self.assertEqual(self.trip.recommendations.count(), 2)

    def test_new_member_clears_recommendations(self):
        self.client.force_login(make_user("khalid"))
        self.client.post(reverse("trips:join"), {"code": self.trip.invite_code})

        self.assertFalse(self.trip.recommendations.exists())

    def test_existing_member_rejoining_keeps_recommendations(self):
        self.client.force_login(self.faisal)
        self.client.post(reverse("trips:join"), {"code": self.trip.invite_code})

        self.assertEqual(self.trip.recommendations.count(), 2)


class RecommendationsPageTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("trips:recommendations", args=[self.trip.pk])

    def test_ready_but_not_generated_organizer_sees_button(self):
        self.client.force_login(self.ammar)

        self.assertContains(self.client.get(self.url), "Generate recommendations")

    def test_ready_but_not_generated_member_waits(self):
        self.client.force_login(self.faisal)
        response = self.client.get(self.url)

        self.assertContains(response, "Waiting for the organizer")
        self.assertNotContains(response, "Generate recommendations</button>")

    def test_not_ready(self):
        TripMember.objects.create(trip=self.trip, user=make_user("khalid"))
        self.client.force_login(self.ammar)

        self.assertContains(self.client.get(self.url), "Not ready yet")

    def test_generated_shows_ranked_cards_and_exclusions(self):
        generate_recommendations(self.trip)
        self.client.force_login(self.faisal)

        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertContains(response, "Top pick")
        self.assertContains(response, "Didn't fit everyone (1)")
        # Bali: 6600 SAR is over both budgets, 13h is over both maximums, Faisal needs direct.
        self.assertContains(response, "Over budget for 2 members · Flight too long for 2 members · "
                                      "No direct flight (1 member needs one)")
        first_city = self.trip.recommendations.get(rank=1).destination.city
        second_city = self.trip.recommendations.get(rank=2).destination.city
        self.assertLess(content.index(first_city), content.index(second_city))

    def test_exclusions_never_name_members(self):
        generate_recommendations(self.trip)
        self.client.force_login(self.ammar)

        excluded_section = self.client.get(self.url).content.decode().split('class="excluded"')[1]

        self.assertNotIn("ammar", excluded_section.lower().split("</details>")[0])
        self.assertNotIn("faisal", excluded_section.lower().split("</details>")[0])

    def test_nothing_fits_state(self):
        self.baku.delete()
        self.cairo.delete()
        self.client.force_login(self.ammar)

        self.assertContains(self.client.get(self.url), "No destination fits everyone")

    def test_non_member_gets_404(self):
        self.client.force_login(make_user("khalid"))

        self.assertEqual(self.client.get(self.url).status_code, 404)


class RecommendationDetailTests(RecommendationTestCase):
    def setUp(self):
        super().setUp()
        generate_recommendations(self.trip)

    def detail_url(self, destination):
        return reverse("trips:recommendation_detail", args=[self.trip.pk, destination.pk])

    def test_shows_reasons_and_member_scores(self):
        self.client.force_login(self.faisal)
        response = self.client.get(self.detail_url(self.baku))

        self.assertContains(response, "Why it fits the group")
        self.assertContains(response, "Fits everyone&#x27;s budget: about 3,300 SAR per person")
        self.assertContains(response, "Direct flight from Riyadh")
        self.assertContains(response, "ammar")
        self.assertContains(response, "faisal")
        self.assertContains(response, "82<small>%</small>")  # stored score 81.7 shown rounded

    def test_member_budgets_are_not_shown(self):
        self.client.force_login(self.faisal)
        content = self.client.get(self.detail_url(self.baku)).content.decode()

        self.assertNotIn("4,000", content)
        self.assertNotIn("5,000", content)

    def test_excluded_destination_gets_404(self):
        self.client.force_login(self.ammar)

        self.assertEqual(self.client.get(self.detail_url(self.bali)).status_code, 404)

    def test_unknown_destination_gets_404(self):
        self.client.force_login(self.ammar)
        url = reverse("trips:recommendation_detail", args=[self.trip.pk, 9999])

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_member_gets_404(self):
        self.client.force_login(make_user("khalid"))

        self.assertEqual(self.client.get(self.detail_url(self.baku)).status_code, 404)
