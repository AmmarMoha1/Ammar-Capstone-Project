from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

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


def clear_recommendations(trip):
    """Delete saved recommendations because the group changed. Returns how many were removed."""
    deleted, _by_model = trip.recommendations.all().delete()
    return deleted


@transaction.atomic
def save_preferences(form, membership):
    """Save a member's preference form and clear the trip's now-outdated recommendations.

    Returns the number of recommendations cleared.
    """
    preference = form.save(commit=False)
    preference.trip_member = membership
    preference.save()
    form.save_m2m()
    return clear_recommendations(membership.trip)


@transaction.atomic
def join_trip(user, invite_code):
    """Add `user` to the trip with this invite code.

    Returns (trip, joined): joined is False when the user was already a member.
    A new member clears the trip's recommendations, since they no longer cover everyone.
    Raises TripActionError when the code is unknown, the trip is not planning,
    or the trip is full.
    """
    # select_for_update locks the trip row (on databases that support it) so two
    # people joining at the same moment cannot push the trip past the member limit.
    trip = Trip.objects.select_for_update().filter(invite_code=invite_code).first()
    if trip is None:
        raise TripActionError(_("No trip uses that code. Check it with your organizer."))

    if trip.members.filter(user=user).exists():
        return trip, False

    if not trip.is_planning:
        if trip.status == Trip.Status.DECIDED:
            raise TripActionError(_("This trip is decided and no longer accepts new members."))
        raise TripActionError(_("This trip is cancelled and no longer accepts new members."))

    if trip.members.count() >= Trip.MAX_MEMBERS:
        raise TripActionError(
            _("This trip is full. A trip can have up to %(max)d members.") % {"max": Trip.MAX_MEMBERS}
        )

    try:
        # A savepoint, so a duplicate-membership error doesn't break the outer transaction.
        with transaction.atomic():
            TripMember.objects.create(trip=trip, user=user)
    except IntegrityError:
        # The same user submitted twice at once; the unique constraint kept one row.
        return trip, False
    clear_recommendations(trip)
    return trip, True


@transaction.atomic
def update_trip(form):
    """Save the organizer's trip edits.

    Dates and departure city change costs, routes and weather, so they clear the
    recommendations; a name change does not. Returns (trip, recommendations_cleared).
    """
    trip = form.save()
    affects_matching = {"departure_city", "start_date", "end_date"} & set(form.changed_data)
    cleared = clear_recommendations(trip) if affects_matching else 0
    return trip, cleared


@transaction.atomic
def finalize_trip(trip, destination_id):
    """Save the organizer's final choice. Only a currently recommended destination can be chosen."""
    trip = Trip.objects.select_for_update().get(pk=trip.pk)
    if not trip.is_planning:
        raise TripActionError(_("Only a trip that is still being planned can be decided."))

    recommendation = trip.recommendations.filter(destination_id=destination_id).first()
    if recommendation is None:
        raise TripActionError(_("You can only choose one of this trip's current recommendations."))

    trip.status = Trip.Status.DECIDED
    trip.selected_destination_id = destination_id
    trip.save(update_fields=["status", "selected_destination", "updated_at"])
    return trip


@transaction.atomic
def cancel_trip(trip):
    """Retire the trip instead of deleting it. A decided trip keeps its chosen destination."""
    if trip.status == Trip.Status.CANCELLED:
        raise TripActionError(_("This trip is already cancelled."))
    trip.status = Trip.Status.CANCELLED
    trip.save(update_fields=["status", "updated_at"])
    return trip


@transaction.atomic
def remove_member(trip, member):
    """Remove a member while planning. Their preference is deleted with them (CASCADE).

    The group changed, so recommendations are cleared. The organizer can't be removed,
    which keeps the rule that every trip has its organizer as a member.
    """
    if not trip.is_planning:
        raise TripActionError(_("Members can only be changed while the trip is being planned."))
    if member.user_id == trip.owner_id:
        raise TripActionError(_("The organizer can't be removed from their own trip."))
    member.delete()
    return clear_recommendations(trip)
