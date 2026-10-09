"""Wajha matching engine.

Pure functions with no database access, so every rule can be tested and
explained with hand-calculated numbers.

How a destination is scored for a group:

1. Estimated cost per person = return flight + daily cost x nights.
2. Hard constraints, checked for every member. If any member fails one,
   the destination is excluded for the whole group:
     - estimated cost must be within the member's budget
     - flight duration must be within the member's maximum
     - a direct route must exist if the member wants direct flights only
3. Member score (0-100) = weighted sum of five factors, each 0-1:
     interests 35, budget comfort 25, weather 20, flight comfort 15, direct 5
4. Group score = 0.7 x average member score + 0.3 x lowest member score,
   so one unhappy member pulls the result down instead of being averaged away.
5. Ranking: group score, then lowest member score, then lower cost,
   then shorter flight, then city name (fully deterministic).
"""

from dataclasses import dataclass, field

WEIGHTS = {
    "interests": 35,
    "budget": 25,
    "weather": 20,
    "flight": 15,
    "direct": 5,
}

AVERAGE_WEIGHT = 0.7
LOWEST_WEIGHT = 0.3

# Budget and flight "comfort" scores fall from 1.0 to 0.5 as you approach the limit.
BUDGET_COMFORT_SHARE = 0.8   # cost at or under 80% of the budget scores 1.0
FLIGHT_COMFORT_SHARE = 0.5   # flights at or under half the maximum score 1.0
SCORE_AT_LIMIT = 0.5

WEATHER_SCALE = ["COLD", "MILD", "WARM", "HOT"]
NO_WEATHER_PREFERENCE = "ANY"

WEAK_FIT_THRESHOLD = 50

# Hard-constraint failure codes.
OVER_BUDGET = "budget"
FLIGHT_TOO_LONG = "flight_time"
NO_DIRECT_FLIGHT = "direct"


@dataclass(frozen=True)
class MemberPreferences:
    member_id: int
    name: str
    max_budget: int
    max_flight_hours: float
    weather: str              # COLD / MILD / WARM / HOT / ANY
    direct_only: bool
    interests: frozenset


@dataclass(frozen=True)
class DestinationOption:
    destination_id: int
    city: str
    country: str
    daily_cost: int
    flight_cost: int           # return fare per person
    flight_hours: float
    direct: bool
    weather: str               # weather during the trip's period
    interests: frozenset


@dataclass(frozen=True)
class MemberMatch:
    member: MemberPreferences
    failures: tuple            # hard-constraint codes; empty when the member can go
    factors: dict              # factor name -> 0..1 (empty when there are failures)
    score: float               # 0..100 (0 when there are failures)
    shared_interests: frozenset

    @property
    def fits(self):
        return not self.failures


@dataclass(frozen=True)
class GroupMatch:
    option: DestinationOption
    estimated_cost: int
    member_matches: tuple
    score: float | None        # None when the destination doesn't fit everyone
    lowest_member_score: float | None
    blocked: dict = field(default_factory=dict)  # failure code -> number of members

    @property
    def fits_everyone(self):
        return self.score is not None

    @property
    def weak_fit_count(self):
        return sum(1 for match in self.member_matches if match.score < WEAK_FIT_THRESHOLD)


# --- Cost -----------------------------------------------------------------

def estimate_trip_cost(option, nights):
    """Per-person estimate: return flight plus daily on-ground cost for each night."""
    return option.flight_cost + option.daily_cost * nights


# --- Hard constraints -----------------------------------------------------

def find_hard_constraint_failures(member, option, cost):
    failures = []
    if cost > member.max_budget:
        failures.append(OVER_BUDGET)
    if option.flight_hours > member.max_flight_hours:
        failures.append(FLIGHT_TOO_LONG)
    if member.direct_only and not option.direct:
        failures.append(NO_DIRECT_FLIGHT)
    return tuple(failures)


# --- Factor scores (each 0..1) ---------------------------------------------

def _comfort(value, limit, comfortable_share):
    """1.0 up to comfortable_share x limit, then falling linearly to 0.5 at the limit."""
    comfortable = limit * comfortable_share
    if value <= comfortable:
        return 1.0
    over = (value - comfortable) / (limit - comfortable)
    return max(0.0, 1.0 - (1.0 - SCORE_AT_LIMIT) * over)


def interest_score(member, option):
    """Share of the member's interests that the destination offers."""
    if not member.interests:
        return 1.0  # nothing requested, so nothing is missing (the form requires at least one)
    return len(member.interests & option.interests) / len(member.interests)


def budget_score(cost, max_budget):
    return _comfort(cost, max_budget, BUDGET_COMFORT_SHARE)


def flight_score(flight_hours, max_flight_hours):
    return _comfort(flight_hours, max_flight_hours, FLIGHT_COMFORT_SHARE)


def weather_score(preferred, actual):
    """Exact match 1.0, neighbouring type (e.g. Cold vs Mild) 0.5, otherwise 0."""
    if preferred == NO_WEATHER_PREFERENCE or preferred == actual:
        return 1.0
    distance = abs(WEATHER_SCALE.index(preferred) - WEATHER_SCALE.index(actual))
    return 0.5 if distance == 1 else 0.0


def direct_score(direct_available):
    return 1.0 if direct_available else 0.5


# --- Member and group matches ---------------------------------------------

def calculate_member_match(member, option, nights):
    cost = estimate_trip_cost(option, nights)
    shared = member.interests & option.interests
    failures = find_hard_constraint_failures(member, option, cost)
    if failures:
        return MemberMatch(member, failures, {}, 0.0, shared)

    factors = {
        "interests": interest_score(member, option),
        "budget": budget_score(cost, member.max_budget),
        "weather": weather_score(member.weather, option.weather),
        "flight": flight_score(option.flight_hours, member.max_flight_hours),
        "direct": direct_score(option.direct),
    }
    score = sum(WEIGHTS[name] * value for name, value in factors.items())
    return MemberMatch(member, (), factors, score, shared)


def combine_member_scores(scores):
    """Group score = 0.7 x average + 0.3 x lowest."""
    if not scores:
        raise ValueError("A group score needs at least one member score.")
    average = sum(scores) / len(scores)
    return AVERAGE_WEIGHT * average + LOWEST_WEIGHT * min(scores)


def calculate_group_match(members, option, nights):
    if not members:
        raise ValueError("A group match needs at least one member.")

    matches = tuple(calculate_member_match(member, option, nights) for member in members)
    cost = estimate_trip_cost(option, nights)

    blocked = {}
    for match in matches:
        for failure in match.failures:
            blocked[failure] = blocked.get(failure, 0) + 1

    if blocked:
        return GroupMatch(option, cost, matches, None, None, blocked)

    scores = [match.score for match in matches]
    return GroupMatch(option, cost, matches, combine_member_scores(scores), min(scores))


def ranking_key(group_match):
    return (
        -group_match.score,
        -group_match.lowest_member_score,
        group_match.estimated_cost,
        group_match.option.flight_hours,
        group_match.option.city,
    )


def rank_destinations(members, options, nights):
    """Return (ranked, excluded).

    ranked: destinations that fit everyone, best first.
    excluded: destinations that failed a hard constraint for at least one member,
    ordered by how few members they block, then by city.
    """
    group_matches = [calculate_group_match(members, option, nights) for option in options]
    ranked = sorted((m for m in group_matches if m.fits_everyone), key=ranking_key)
    excluded = sorted(
        (m for m in group_matches if not m.fits_everyone),
        key=lambda m: (sum(1 for mm in m.member_matches if not mm.fits), m.option.city),
    )
    return ranked, excluded
