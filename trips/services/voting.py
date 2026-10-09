"""Group vote on the top recommendations: one vote per member, the organizer still decides."""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext as _

from ..models import Vote
from .trip_actions import TripActionError


@dataclass(frozen=True)
class VoteSummary:
    options: list           # top recommendations, each annotated with vote_count
    voted: int              # members who have voted
    members: int            # all members of the trip
    leader: object          # the recommendation with the most votes, or None (no votes or a tie)
    my_destination_id: int  # destination the current member voted for, or None


def voting_options(trip):
    """The top recommendations members can vote for, with their vote counts.

    Annotation: Count("votes") adds each recommendation's number of votes in the same query.
    """
    return (
        trip.recommendations.filter(rank__lte=Vote.MAX_RANK)
        .select_related("destination")
        .annotate(vote_count=Count("votes"))
        .order_by("rank")
    )


def vote_summary(trip, membership):
    options = list(voting_options(trip))
    most = max((option.vote_count for option in options), default=0)
    leaders = [option for option in options if most and option.vote_count == most]
    my_vote = Vote.objects.filter(trip_member=membership).select_related("recommendation").first()
    return VoteSummary(
        options=options,
        voted=sum(option.vote_count for option in options),
        members=trip.members.count(),
        leader=leaders[0] if len(leaders) == 1 else None,
        my_destination_id=my_vote.recommendation.destination_id if my_vote else None,
    )


@transaction.atomic
def cast_vote(membership, destination_id):
    """Record or change a member's vote. Only a top-3 recommendation of a planning trip can be chosen."""
    trip = membership.trip
    if not trip.is_planning:
        raise TripActionError(_("Voting is closed because the trip is no longer being planned."))

    recommendation = trip.recommendations.filter(destination_id=destination_id, rank__lte=Vote.MAX_RANK).first()
    if recommendation is None:
        raise TripActionError(_("You can only vote for one of the top 3 recommendations."))

    vote, _created = Vote.objects.update_or_create(
        trip_member=membership, defaults={"recommendation": recommendation}
    )
    return vote
