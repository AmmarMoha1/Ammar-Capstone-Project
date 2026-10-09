import secrets
from dataclasses import dataclass

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, F, Q

from destinations.models import Destination, Interest, OriginCity

INVITE_CODE_PREFIX = "WJ-"
# No 0/O or 1/I so codes are easy to read aloud and type.
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 5


def generate_invite_code():
    """Return a random code such as WJ-8K32L (uniqueness is checked by the caller)."""
    suffix = "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))
    return INVITE_CODE_PREFIX + suffix


@dataclass(frozen=True)
class Readiness:
    """How many members have submitted preferences for a trip."""

    total: int
    ready: int

    @property
    def waiting(self):
        return self.total - self.ready

    @property
    def has_enough_members(self):
        return self.total >= Trip.MIN_MEMBERS

    @property
    def all_ready(self):
        return self.total > 0 and self.ready == self.total


class Trip(models.Model):
    """A group trip whose destination the members decide together."""

    MIN_MEMBERS = 2
    MAX_MEMBERS = 8

    class Status(models.TextChoices):
        PLANNING = "PLANNING", "Planning"
        DECIDED = "DECIDED", "Decided"
        CANCELLED = "CANCELLED", "Cancelled"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_trips"
    )
    departure_city = models.ForeignKey(
        OriginCity, on_delete=models.PROTECT, related_name="trips"
    )
    selected_destination = models.ForeignKey(
        Destination,
        on_delete=models.PROTECT,
        related_name="selected_by_trips",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    invite_code = models.CharField(max_length=8, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLANNING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="trip_end_after_start",
            ),
            # PLANNING has no destination yet, DECIDED must have one, and a
            # CANCELLED trip keeps whatever it had (it may have been decided first).
            models.CheckConstraint(
                condition=(
                    Q(status="PLANNING", selected_destination__isnull=True)
                    | Q(status="DECIDED", selected_destination__isnull=False)
                    | Q(status="CANCELLED")
                ),
                name="trip_status_matches_selected_destination",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def nights(self):
        return (self.end_date - self.start_date).days

    @property
    def is_planning(self):
        return self.status == self.Status.PLANNING

    def is_organizer(self, user):
        return self.owner_id == user.id

    def get_readiness(self):
        # Aggregation: Count("preference") only counts members whose preference exists.
        counts = self.members.aggregate(total=Count("id"), ready=Count("preference"))
        return Readiness(**counts)

    def can_generate_recommendations(self, readiness=None):
        """Planning, at least MIN_MEMBERS members, and every member has submitted preferences.

        Pass an already-calculated Readiness to avoid querying it again.
        """
        readiness = readiness or self.get_readiness()
        return self.is_planning and readiness.has_enough_members and readiness.all_ready


class TripMember(models.Model):
    """A user's membership in a trip. The organizer is always a member too."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trip_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(fields=["trip", "user"], name="unique_trip_member"),
        ]

    def __str__(self):
        return f"{self.user} in {self.trip}"

    @property
    def has_preferences(self):
        # A missing reverse one-to-one raises an AttributeError subclass, so hasattr works.
        return hasattr(self, "preference")


class WeatherPreference(models.TextChoices):
    # Same values as destinations.WeatherType, plus "no preference".
    COLD = "COLD", "Cold"
    MILD = "MILD", "Mild"
    WARM = "WARM", "Warm"
    HOT = "HOT", "Hot"
    ANY = "ANY", "No preference"


class Preference(models.Model):
    """One member's travel preferences for one trip.

    max_budget is the maximum total cost per person for the whole trip:
    return flight + estimated daily cost x nights, in SAR.
    """

    MIN_BUDGET = 500
    MAX_BUDGET = 100_000
    MIN_FLIGHT_HOURS = 1
    MAX_FLIGHT_HOURS = 24

    trip_member = models.OneToOneField(
        TripMember, on_delete=models.CASCADE, related_name="preference"
    )
    max_budget = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_BUDGET), MaxValueValidator(MAX_BUDGET)]
    )
    max_flight_hours = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(MIN_FLIGHT_HOURS), MaxValueValidator(MAX_FLIGHT_HOURS)],
    )
    weather_preference = models.CharField(
        max_length=4, choices=WeatherPreference.choices, default=WeatherPreference.ANY
    )
    direct_only = models.BooleanField(default=False)
    interests = models.ManyToManyField(Interest, related_name="preferences")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(max_budget__gt=0), name="preference_budget_positive"
            ),
            models.CheckConstraint(
                condition=Q(max_flight_hours__gt=0), name="preference_flight_hours_positive"
            ),
        ]

    def __str__(self):
        return f"Preferences of {self.trip_member}"


class Recommendation(models.Model):
    """A saved, ranked destination for a trip, produced by the matching engine.

    Rows are replaced whenever recommendations are regenerated and deleted whenever
    the group changes, so they always match the current members and preferences.
    """

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="recommendations")
    destination = models.ForeignKey(
        Destination, on_delete=models.PROTECT, related_name="recommendations"
    )
    rank = models.PositiveSmallIntegerField()
    score = models.DecimalField(max_digits=4, decimal_places=1)
    lowest_member_score = models.DecimalField(max_digits=4, decimal_places=1)
    estimated_total_cost = models.PositiveIntegerField(help_text="Estimated SAR per person.")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["trip", "rank"]
        constraints = [
            models.UniqueConstraint(fields=["trip", "destination"], name="unique_recommendation_destination"),
            models.UniqueConstraint(fields=["trip", "rank"], name="unique_recommendation_rank"),
            models.CheckConstraint(condition=Q(rank__gte=1), name="recommendation_rank_positive"),
            models.CheckConstraint(
                condition=Q(score__gte=0, score__lte=100), name="recommendation_score_range"
            ),
            models.CheckConstraint(
                condition=Q(lowest_member_score__gte=0, lowest_member_score__lte=100),
                name="recommendation_lowest_score_range",
            ),
        ]

    def __str__(self):
        return f"#{self.rank} {self.destination.city} for {self.trip} ({self.score}%)"
