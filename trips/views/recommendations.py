"""Recommendations: generate, list, explain, finalize, and the group vote on the top 3."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, ngettext

from ..permissions import get_member_trip_or_404, get_organizer_trip_or_403
from ..services.matching import WEIGHTS, match_band
from ..services.recommendations import (
    describe_exclusion,
    evaluate_trip,
    explain_group_match,
    generate_recommendations,
)
from ..services.trip_actions import TripActionError, finalize_trip
from ..services.voting import cast_vote, vote_summary


FACTOR_LABELS = {
    "interests": gettext_lazy("Interests"),
    "budget": gettext_lazy("Budget comfort"),
    "weather": gettext_lazy("Weather"),
    "flight": gettext_lazy("Flight comfort"),
    "direct": gettext_lazy("Direct flight"),
}


def _shared_interests(match):
    """Interests the destination offers that at least one member wants."""
    if match is None:
        return []
    return sorted(_(name) for name in set().union(*(m.shared_interests for m in match.member_matches)))


def _factor_rows(match):
    """Group average for each scoring factor, as a percentage, with its weight."""
    count = len(match.member_matches)
    return [
        {
            "label": label,
            "weight": WEIGHTS[name],
            "percent": round(100 * sum(m.factors[name] for m in match.member_matches) / count),
        }
        for name, label in FACTOR_LABELS.items()
    ]


@login_required
def recommendations_generate(request, pk):
    trip = get_organizer_trip_or_403(request.user, pk)
    if request.method != "POST":
        return redirect("trips:recommendations", pk=trip.pk)

    try:
        count = generate_recommendations(trip)
    except TripActionError as error:
        messages.error(request, str(error))
        return redirect("trips:detail", pk=trip.pk)

    if count:
        messages.success(request, ngettext(
            "Recommendations are ready: %(count)d destination fits everyone.",
            "Recommendations are ready: %(count)d destinations fit everyone.",
            count,
        ) % {"count": count})
    else:
        messages.warning(request, _("No destination fits everyone yet. See what is blocking each one below."))
    return redirect("trips:recommendations", pk=trip.pk)


@login_required
def recommendations(request, pk):
    trip = get_member_trip_or_404(request.user, pk)
    # Ordering: saved recommendations are shown by rank (best match first).
    saved = list(trip.recommendations.select_related("destination").order_by("rank"))
    can_generate = trip.can_generate_recommendations()

    # The engine is deterministic, so running it on current data tells us the excluded
    # destinations and the facts (flight, weather, interests) for each saved card.
    ranked, excluded = evaluate_trip(trip) if (saved or can_generate) else ([], [])
    live = {match.option.destination_id: match for match in ranked}

    cards = []
    for rec in saved:
        match = live.get(rec.destination_id)
        cards.append({
            "recommendation": rec,
            "match": match,
            "band": _(match_band(rec.score)),
            "interests": _shared_interests(match),
        })
    return render(
        request,
        "trips/recommendations.html",
        {
            "trip": trip,
            "is_organizer": trip.is_organizer(request.user),
            "cards": cards,
            "can_generate": can_generate,
            "nothing_fits": can_generate and not ranked,
            "excluded": [(match, describe_exclusion(match)) for match in excluded],
            "votes": vote_summary(trip, trip.members.get(user=request.user)) if saved else None,
        },
    )


@login_required
def recommendation_detail(request, pk, destination_id):
    trip = get_member_trip_or_404(request.user, pk)
    recommendation = get_object_or_404(
        trip.recommendations.select_related("destination"), destination_id=destination_id
    )
    ranked, _excluded = evaluate_trip(trip)
    match = next((m for m in ranked if m.option.destination_id == destination_id), None)

    member_rows, factor_rows = [], []
    if match:
        member_rows = sorted(match.member_matches, key=lambda m: -m.score)
        factor_rows = _factor_rows(match)

    return render(
        request,
        "trips/recommendation_detail.html",
        {
            "trip": trip,
            "is_organizer": trip.is_organizer(request.user),
            "recommendation": recommendation,
            "band": _(match_band(recommendation.score)),
            "match": match,
            "reasons": explain_group_match(match, trip) if match else [],
            "member_rows": member_rows,
            "factor_rows": factor_rows,
            "interests": _shared_interests(match),
        },
    )


@login_required
def trip_finalize(request, pk, destination_id):
    trip = get_organizer_trip_or_403(request.user, pk)
    recommendation = get_object_or_404(
        trip.recommendations.select_related("destination"), destination_id=destination_id
    )
    if request.method == "POST":
        try:
            finalize_trip(trip, destination_id)
        except TripActionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, _("Decision saved: %(city)s it is!") % {"city": _(recommendation.destination.city)})
        return redirect("trips:detail", pk=trip.pk)

    if not trip.is_planning:
        messages.error(request, _("Only a trip that is still being planned can be decided."))
        return redirect("trips:detail", pk=trip.pk)

    city = _(recommendation.destination.city)
    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": _("Choose %(city)s for %(trip)s?") % {"city": city, "trip": trip.name},
        "consequences": [
            _("%(city)s becomes the group's destination, with a %(score)s%% Group Match.") % {
                "city": city, "score": f"{recommendation.score:.0f}",
            },
            _("The trip becomes Decided and is locked: no more joining, preference changes or new recommendations."),
            _("All members will see the decision in the Trip Room."),
        ],
        "confirm_label": _("Choose %(city)s") % {"city": city},
        "confirm_style": "primary",
        "back_label": _("Not yet"),
        "back_url": reverse("trips:recommendation_detail", args=[trip.pk, destination_id]),
    })


# --- Group vote ------------------------------------------------------------------

@login_required
def vote(request, pk, destination_id):
    trip = get_member_trip_or_404(request.user, pk)
    if request.method != "POST":
        return redirect("trips:recommendations", pk=trip.pk)

    membership = trip.members.get(user=request.user)
    try:
        saved = cast_vote(membership, destination_id)
    except TripActionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, _("Your vote for %(city)s was saved.") % {
            "city": _(saved.recommendation.destination.city),
        })
    return redirect(reverse("trips:recommendations", args=[trip.pk]) + "#vote")
