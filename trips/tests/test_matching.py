"""Matching engine tests. Expected values are calculated by hand in the comments."""

from django.test import SimpleTestCase

from trips.services.matching import (
    FLIGHT_TOO_LONG,
    NO_DIRECT_FLIGHT,
    OVER_BUDGET,
    DestinationOption,
    GroupMatch,
    MemberPreferences,
    budget_score,
    calculate_group_match,
    calculate_member_match,
    combine_member_scores,
    direct_score,
    estimate_trip_cost,
    flight_score,
    interest_score,
    rank_destinations,
    ranking_key,
    weather_score,
)

NIGHTS = 4


def member(name="Ammar", budget=4000, hours=5, weather="COLD", direct_only=False,
           interests=("Nature", "Food"), member_id=1):
    return MemberPreferences(member_id, name, budget, hours, weather, direct_only, frozenset(interests))


def option(city="Baku", daily=450, flight_cost=1500, hours=3.5, direct=True, weather="COLD",
           interests=("Culture", "Food", "Nightlife"), destination_id=1):
    return DestinationOption(destination_id, city, "Country", daily, flight_cost, hours, direct,
                             weather, frozenset(interests))


AMMAR = member()
FAISAL = member("Faisal", budget=5000, hours=6, weather="MILD", direct_only=True,
                interests=("Culture", "Food"), member_id=2)
BAKU = option()


class CostTests(SimpleTestCase):
    def test_flight_plus_daily_cost_times_nights(self):
        # 1500 + 450 x 4 = 3300
        self.assertEqual(estimate_trip_cost(BAKU, NIGHTS), 3300)


class FactorTests(SimpleTestCase):
    def test_interest_share(self):
        # Ammar wants Nature and Food; Baku offers Food -> 1 of 2
        self.assertEqual(interest_score(AMMAR, BAKU), 0.5)
        self.assertEqual(interest_score(FAISAL, BAKU), 1.0)
        self.assertEqual(interest_score(member(interests=("Beaches",)), BAKU), 0.0)

    def test_budget_comfort(self):
        self.assertEqual(budget_score(3000, 4000), 1.0)    # under 80% (3200)
        self.assertEqual(budget_score(3200, 4000), 1.0)    # exactly 80%
        self.assertEqual(budget_score(3300, 4000), 0.9375) # 1 - 0.5 x (100 / 800)
        self.assertEqual(budget_score(4000, 4000), 0.5)    # at the limit

    def test_flight_comfort(self):
        self.assertEqual(flight_score(2.5, 5), 1.0)  # half the maximum
        self.assertEqual(flight_score(3.5, 5), 0.8)  # 1 - 0.5 x (1 / 2.5)
        self.assertEqual(flight_score(5, 5), 0.5)    # at the limit

    def test_weather(self):
        self.assertEqual(weather_score("COLD", "COLD"), 1.0)
        self.assertEqual(weather_score("ANY", "HOT"), 1.0)
        self.assertEqual(weather_score("COLD", "MILD"), 0.5)
        self.assertEqual(weather_score("WARM", "HOT"), 0.5)
        self.assertEqual(weather_score("COLD", "WARM"), 0.0)
        self.assertEqual(weather_score("COLD", "HOT"), 0.0)

    def test_direct(self):
        self.assertEqual(direct_score(True), 1.0)
        self.assertEqual(direct_score(False), 0.5)


class HardConstraintTests(SimpleTestCase):
    def test_over_budget(self):
        match = calculate_member_match(member(budget=3299), BAKU, NIGHTS)  # cost 3300

        self.assertEqual(match.failures, (OVER_BUDGET,))
        self.assertFalse(match.fits)
        self.assertEqual(match.score, 0)

    def test_exactly_at_budget_is_allowed(self):
        self.assertTrue(calculate_member_match(member(budget=3300), BAKU, NIGHTS).fits)

    def test_flight_too_long(self):
        match = calculate_member_match(member(hours=3), BAKU, NIGHTS)  # flight 3.5

        self.assertEqual(match.failures, (FLIGHT_TOO_LONG,))

    def test_exactly_at_flight_limit_is_allowed(self):
        self.assertTrue(calculate_member_match(member(hours=3.5), BAKU, NIGHTS).fits)

    def test_direct_only_without_direct_route(self):
        match = calculate_member_match(member(direct_only=True), option(direct=False), NIGHTS)

        self.assertEqual(match.failures, (NO_DIRECT_FLIGHT,))

    def test_indirect_route_is_fine_when_not_direct_only(self):
        self.assertTrue(calculate_member_match(member(direct_only=False), option(direct=False), NIGHTS).fits)

    def test_several_failures_are_all_reported(self):
        match = calculate_member_match(
            member(budget=1000, hours=2, direct_only=True), option(direct=False), NIGHTS
        )

        self.assertEqual(match.failures, (OVER_BUDGET, FLIGHT_TOO_LONG, NO_DIRECT_FLIGHT))


class MemberScoreTests(SimpleTestCase):
    def test_ammar_in_baku(self):
        # interests 0.5 x 35 = 17.5
        # budget 0.9375 x 25 = 23.4375   (cost 3300, budget 4000)
        # weather 1.0 x 20 = 20          (Cold = Cold)
        # flight 0.8 x 15 = 12           (3.5h of max 5h)
        # direct 1.0 x 5 = 5
        # total = 77.9375
        match = calculate_member_match(AMMAR, BAKU, NIGHTS)

        self.assertAlmostEqual(match.score, 77.9375)
        self.assertEqual(match.shared_interests, frozenset({"Food"}))

    def test_faisal_in_baku(self):
        # interests 1.0 x 35 = 35
        # budget 1.0 x 25 = 25            (3300 is under 80% of 5000)
        # weather 0.5 x 20 = 10           (wants Mild, Baku is Cold)
        # flight 0.91667 x 15 = 13.75     (1 - 0.5 x (0.5 / 3))
        # direct 1.0 x 5 = 5
        # total = 88.75
        self.assertAlmostEqual(calculate_member_match(FAISAL, BAKU, NIGHTS).score, 88.75)

    def test_perfect_match_scores_100(self):
        perfect = member(budget=10000, hours=10, interests=("Food",))

        self.assertAlmostEqual(calculate_member_match(perfect, BAKU, NIGHTS).score, 100)


class GroupScoreTests(SimpleTestCase):
    def test_formula_example_from_plan(self):
        # average 93, lowest 89 -> 0.7 x 93 + 0.3 x 89 = 65.1 + 26.7 = 91.8
        self.assertAlmostEqual(combine_member_scores([96, 89, 94, 93]), 91.8)

    def test_unhappy_member_pulls_score_down(self):
        # average 85, lowest 40 -> 59.5 + 12 = 71.5 (a plain average would say 85)
        self.assertAlmostEqual(combine_member_scores([100, 100, 100, 40]), 71.5)

    def test_single_score(self):
        self.assertAlmostEqual(combine_member_scores([80]), 80)

    def test_empty_scores_are_rejected(self):
        with self.assertRaises(ValueError):
            combine_member_scores([])

    def test_ammar_and_faisal_in_baku(self):
        # average (77.9375 + 88.75) / 2 = 83.34375
        # 0.7 x 83.34375 + 0.3 x 77.9375 = 58.340625 + 23.38125 = 81.721875
        group = calculate_group_match([AMMAR, FAISAL], BAKU, NIGHTS)

        self.assertTrue(group.fits_everyone)
        self.assertAlmostEqual(group.score, 81.721875)
        self.assertAlmostEqual(group.lowest_member_score, 77.9375)
        self.assertEqual(group.estimated_cost, 3300)

    def test_one_failing_member_excludes_destination(self):
        khalid = member("Khalid", budget=3000, member_id=3)
        group = calculate_group_match([AMMAR, FAISAL, khalid], BAKU, NIGHTS)

        self.assertFalse(group.fits_everyone)
        self.assertIsNone(group.score)
        self.assertEqual(group.blocked, {OVER_BUDGET: 1})

    def test_blocked_counts_are_per_reason(self):
        tight = member("A", budget=3000, member_id=3)
        tighter = member("B", budget=2000, hours=3, member_id=4)
        group = calculate_group_match([AMMAR, tight, tighter], BAKU, NIGHTS)

        self.assertEqual(group.blocked, {OVER_BUDGET: 2, FLIGHT_TOO_LONG: 1})

    def test_weak_fit_count(self):
        # Ammar wants Beaches only and Hot weather: interests 0, weather 0 -> 23.4375 + 12 + 5 = 40.4375
        unhappy = member(weather="HOT", interests=("Beaches",))
        group = calculate_group_match([unhappy, FAISAL], BAKU, NIGHTS)

        self.assertEqual(group.weak_fit_count, 1)

    def test_no_members_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_group_match([], BAKU, NIGHTS)


class RankingTests(SimpleTestCase):
    def ranked_cities(self, matches):
        return [m.option.city for m in sorted(matches, key=ranking_key)]

    def group(self, city, score, lowest, cost=3000, hours=4.0):
        return GroupMatch(option(city=city, hours=hours), cost, (), score, lowest)

    def test_higher_score_first(self):
        self.assertEqual(self.ranked_cities([self.group("A", 70, 60), self.group("B", 90, 80)]), ["B", "A"])

    def test_tie_broken_by_lowest_member_score(self):
        self.assertEqual(self.ranked_cities([self.group("A", 80, 70), self.group("B", 80, 75)]), ["B", "A"])

    def test_then_by_lower_cost(self):
        matches = [self.group("A", 80, 70, cost=3000), self.group("B", 80, 70, cost=2500)]
        self.assertEqual(self.ranked_cities(matches), ["B", "A"])

    def test_then_by_shorter_flight(self):
        matches = [self.group("A", 80, 70, hours=4), self.group("B", 80, 70, hours=3)]
        self.assertEqual(self.ranked_cities(matches), ["B", "A"])

    def test_then_by_city_name(self):
        self.assertEqual(self.ranked_cities([self.group("Tbilisi", 80, 70), self.group("Baku", 80, 70)]),
                         ["Baku", "Tbilisi"])

    def test_rank_destinations_splits_ranked_and_excluded(self):
        cairo = option("Cairo", daily=350, flight_cost=1100, hours=2.5, weather="MILD",
                       interests=("Culture", "Food", "Shopping"), destination_id=2)
        bali = option("Bali", daily=600, flight_cost=4200, hours=13, direct=False, weather="HOT",
                      interests=("Beaches", "Nature"), destination_id=3)

        ranked, excluded = rank_destinations([AMMAR, FAISAL], [BAKU, cairo, bali], NIGHTS)

        self.assertEqual([m.option.city for m in excluded], ["Bali"])
        self.assertEqual(len(ranked), 2)
        self.assertGreaterEqual(ranked[0].score, ranked[1].score)

    def test_no_options(self):
        self.assertEqual(rank_destinations([AMMAR], [], NIGHTS), ([], []))
