import secrets

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from destinations.models import Destination, OriginCity

INVITE_CODE_PREFIX = "WJ-"
# No 0/O or 1/I/L so codes are easy to read aloud and type.
INVITE_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 5


def generate_invite_code():
    """Return a random code such as WJ-8K32L (uniqueness is checked by the caller)."""
    suffix = "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))
    return INVITE_CODE_PREFIX + suffix


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
