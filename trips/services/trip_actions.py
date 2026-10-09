from django.db import transaction

from ..models import Trip, TripMember, generate_invite_code

MAX_CODE_ATTEMPTS = 10


def unique_invite_code():
    """Generate invite codes until one is not used by any trip.

    With 31^5 (about 28 million) possible codes a clash is very unlikely; the
    unique constraint on Trip.invite_code is the final safeguard.
    """
    for _ in range(MAX_CODE_ATTEMPTS):
        code = generate_invite_code()
        if not Trip.objects.filter(invite_code=code).exists():
            return code
    raise RuntimeError("Could not generate a unique invite code.")


@transaction.atomic
def create_trip(owner, **fields):
    """Create a trip and its organizer membership together.

    Both rows are saved in one transaction, so a trip can never exist
    without its organizer as a TripMember.
    """
    trip = Trip.objects.create(owner=owner, invite_code=unique_invite_code(), **fields)
    TripMember.objects.create(trip=trip, user=owner)
    return trip
