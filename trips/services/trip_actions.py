from django.db import IntegrityError, transaction

from ..models import Trip, TripMember, generate_invite_code

MAX_CODE_ATTEMPTS = 10


class TripActionError(Exception):
    """A business rule stopped the action. The message is safe to show to the user."""


def unique_invite_code():
    """Generate invite codes until one is not used by any trip.

    With 32^5 (about 33 million) possible codes a clash is very unlikely; the
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


@transaction.atomic
def join_trip(user, invite_code):
    """Add `user` to the trip with this invite code.

    Returns (trip, joined): joined is False when the user was already a member.
    Raises TripActionError when the code is unknown, the trip is not planning,
    or the trip is full.
    """
    # select_for_update locks the trip row (on databases that support it) so two
    # people joining at the same moment cannot push the trip past the member limit.
    trip = Trip.objects.select_for_update().filter(invite_code=invite_code).first()
    if trip is None:
        raise TripActionError("No trip uses that code. Check it with your organizer.")

    if trip.members.filter(user=user).exists():
        return trip, False

    if not trip.is_planning:
        raise TripActionError(
            f"This trip is {trip.get_status_display().lower()} and no longer accepts new members."
        )

    if trip.members.count() >= Trip.MAX_MEMBERS:
        raise TripActionError(f"This trip is full. A trip can have up to {Trip.MAX_MEMBERS} members.")

    try:
        # A savepoint, so a duplicate-membership error doesn't break the outer transaction.
        with transaction.atomic():
            TripMember.objects.create(trip=trip, user=user)
    except IntegrityError:
        # The same user submitted twice at once; the unique constraint kept one row.
        return trip, False
    return trip, True
