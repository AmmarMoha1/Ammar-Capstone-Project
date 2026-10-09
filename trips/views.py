from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import JoinTripForm, PreferenceForm, TripForm
from .models import Preference, Trip, TripMember
from .permissions import get_member_trip_or_404, get_organizer_trip_or_403
from .services.matching import WEIGHTS, match_band
from .services.recommendations import (
    describe_exclusion,
    evaluate_trip,
    explain_group_match,
    generate_recommendations,
)
from .services.trip_actions import TripActionError, create_trip, join_trip, save_preferences


def home(request):
    if request.user.is_authenticated:
        return redirect("trips:my_trips")
    return render(request, "trips/home.html")


@login_required
def my_trips(request):
    # Relationship query: trips where the current user is a member (organizer included).
    # A subquery is used instead of filter(members__user=...) because that filter would
    # reuse the members join and make Count("members") count only the user's own row.
    my_trip_ids = TripMember.objects.filter(user=request.user).values("trip_id")
    trips = (
        Trip.objects.filter(pk__in=my_trip_ids)
        .select_related("departure_city", "selected_destination")
        .annotate(member_count=Count("members", distinct=True))
        .order_by("-created_at")
    )
    return render(request, "trips/my_trips.html", {"trips": trips})


@login_required
def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            trip = create_trip(request.user, **form.cleaned_data)
            messages.success(
                request,
                f"Trip created. Share the code {trip.invite_code} with your friends.",
            )
            return redirect("trips:detail", pk=trip.pk)
    else:
        form = TripForm()

    return render(request, "trips/trip_form.html", {"form": form})


@login_required
def trip_join(request):
    if request.method == "POST":
        form = JoinTripForm(request.POST)
        if form.is_valid():
            try:
                trip, joined = join_trip(request.user, form.cleaned_data["code"])
            except TripActionError as error:
                form.add_error("code", str(error))
            else:
                if joined:
                    messages.success(request, f"You joined {trip.name}. Next, add your preferences.")
                else:
                    messages.info(request, f"You're already a member of {trip.name}.")
                return redirect("trips:detail", pk=trip.pk)
    else:
        form = JoinTripForm()

    return render(request, "trips/trip_join.html", {"form": form})


@login_required
def trip_detail(request, pk):
    trip = get_member_trip_or_404(request.user, pk)
    # select_related("preference") loads each member's preference (if any) in the same query.
    members = list(trip.members.select_related("user", "preference"))
    my_membership = next(member for member in members if member.user_id == request.user.id)
    readiness = trip.get_readiness()

    return render(
        request,
        "trips/trip_detail.html",
        {
            "trip": trip,
            "members": members,
            "is_organizer": trip.is_organizer(request.user),
            "my_membership": my_membership,
            "readiness": readiness,
            "can_generate": trip.can_generate_recommendations(readiness),
            "top_recommendation": trip.recommendations.select_related("destination").first(),
        },
    )


@login_required
def preferences(request, pk):
    trip = get_member_trip_or_404(request.user, pk)
    if not trip.is_planning:
        messages.error(request, "Preferences can only be changed while the trip is being planned.")
        return redirect("trips:detail", pk=trip.pk)

    # Always the current user's own membership: there is no way to address someone else's.
    membership = trip.members.get(user=request.user)
    existing = Preference.objects.filter(trip_member=membership).first()

    if request.method == "POST":
        form = PreferenceForm(request.POST, instance=existing)
        if form.is_valid():
            cleared = save_preferences(form, membership)
            messages.success(request, "Your preferences were saved.")
            if cleared:
                messages.info(request, "Recommendations were cleared because the group's preferences changed.")
            return redirect("trips:detail", pk=trip.pk)
    else:
        form = PreferenceForm(instance=existing)

    return render(
        request,
        "trips/preferences.html",
        {"trip": trip, "form": form, "is_update": existing is not None},
    )


FACTOR_LABELS = {
    "interests": "Interests",
    "budget": "Budget comfort",
    "weather": "Weather",
    "flight": "Flight comfort",
    "direct": "Direct flight",
}


def _shared_interests(match):
    """Interests the destination offers that at least one member wants."""
    if match is None:
        return []
    return sorted(set().union(*(m.shared_interests for m in match.member_matches)))


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
        messages.success(
            request, f"Recommendations are ready: {count} destination{'s' if count != 1 else ''} fit everyone."
        )
    else:
        messages.warning(request, "No destination fits everyone yet. See what is blocking each one below.")
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
            "band": match_band(rec.score),
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
        },
    )


@login_required
def recommendation_detail(request, pk, destination_id):
    trip = get_member_trip_or_404(request.user, pk)
    recommendation = get_object_or_404(
        trip.recommendations.select_related("destination"), destination_id=destination_id
    )
    ranked, _ = evaluate_trip(trip)
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
            "band": match_band(recommendation.score),
            "match": match,
            "reasons": explain_group_match(match, trip) if match else [],
            "member_rows": member_rows,
            "factor_rows": factor_rows,
            "interests": _shared_interests(match),
        },
    )
