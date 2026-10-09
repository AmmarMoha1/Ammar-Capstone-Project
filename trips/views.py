from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from destinations.photos import all_photos

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
from .services.summary import MIN_SUBMISSIONS_FOR_BUDGETS, group_summary
from .services.trip_actions import (
    TripActionError,
    cancel_trip,
    create_trip,
    finalize_trip,
    join_trip,
    remove_member,
    save_preferences,
    update_trip,
)


def credits(request):
    return render(request, "credits.html", {"photos": all_photos()})


def home(request):
    if request.user.is_authenticated:
        return redirect("trips:my_trips")
    return render(request, "trips/home.html")


STATUS_FILTERS = {
    "planning": Trip.Status.PLANNING,
    "decided": Trip.Status.DECIDED,
    "cancelled": Trip.Status.CANCELLED,
}


@login_required
def my_trips(request):
    # Relationship query: trips where the current user is a member (organizer included).
    # A subquery is used instead of filter(members__user=...) because that filter would
    # reuse the members join and make Count("members") count only the user's own row.
    my_trip_ids = TripMember.objects.filter(user=request.user).values("trip_id")
    my_trips_qs = Trip.objects.filter(pk__in=my_trip_ids)

    # Aggregation: how many of my trips are in each status (for the filter tabs).
    status_counts = my_trips_qs.aggregate(
        all=Count("id"),
        planning=Count("id", filter=Q(status=Trip.Status.PLANNING)),
        decided=Count("id", filter=Q(status=Trip.Status.DECIDED)),
        cancelled=Count("id", filter=Q(status=Trip.Status.CANCELLED)),
    )

    # Filtering: an unknown ?status= value simply shows all trips.
    active_filter = request.GET.get("status", "").lower()
    if active_filter not in STATUS_FILTERS:
        active_filter = "all"
    else:
        my_trips_qs = my_trips_qs.filter(status=STATUS_FILTERS[active_filter])

    # Annotation: per-trip member and ready counts. Preference is one-to-one with TripMember,
    # so both counts use the same join today; distinct=True keeps them correct if another
    # one-to-many count (e.g. recommendations) is added, which would otherwise multiply rows.
    trips = (
        my_trips_qs.select_related("departure_city", "selected_destination")
        .annotate(
            member_count=Count("members", distinct=True),
            ready_count=Count("members__preference", distinct=True),
        )
        .order_by("-created_at")
    )

    filters = [
        {"key": key, "label": label, "count": status_counts[key]}
        for key, label in [("all", "All"), ("planning", "Planning"), ("decided", "Decided"), ("cancelled", "Cancelled")]
    ]
    return render(request, "trips/my_trips.html", {
        "trips": trips,
        "filters": filters,
        "active_filter": active_filter,
        "has_any_trips": status_counts["all"] > 0,
    })


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
def trip_edit(request, pk):
    trip = get_organizer_trip_or_403(request.user, pk)
    if not trip.is_planning:
        messages.error(request, "Only a trip that is still being planned can be edited.")
        return redirect("trips:detail", pk=trip.pk)

    if request.method == "POST":
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            trip, cleared = update_trip(form)
            messages.success(request, "Trip details were updated.")
            if cleared:
                messages.info(request, "Recommendations were cleared because the dates or departure city changed.")
            return redirect("trips:detail", pk=trip.pk)
    else:
        form = TripForm(instance=trip)

    return render(request, "trips/trip_form.html", {"form": form, "trip": trip})


@login_required
def trip_cancel(request, pk):
    trip = get_organizer_trip_or_403(request.user, pk)
    if request.method == "POST":
        try:
            cancel_trip(trip)
        except TripActionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"{trip.name} was cancelled.")
        return redirect("trips:detail", pk=trip.pk)

    if trip.status == Trip.Status.CANCELLED:
        messages.info(request, "This trip is already cancelled.")
        return redirect("trips:detail", pk=trip.pk)

    consequences = [
        "Members can still open the trip, but nothing can be changed afterwards.",
        "No one can join, edit preferences or generate recommendations.",
        "This can't be undone.",
    ]
    if trip.selected_destination:
        consequences.insert(0, f"The decision for {trip.selected_destination.city} stays on record as cancelled.")
    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": f"Cancel {trip.name}?",
        "consequences": consequences,
        "confirm_label": "Cancel trip",
        "confirm_style": "danger",
        "back_label": "Keep trip",
    })


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
            "decision": _decision(trip),
            "summary": group_summary(trip),
            "budget_threshold": MIN_SUBMISSIONS_FOR_BUDGETS,
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


def _decision(trip):
    """The saved recommendation for the chosen destination (for the decision card)."""
    if trip.selected_destination_id is None:
        return None
    return trip.recommendations.filter(destination_id=trip.selected_destination_id).first()


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
            messages.success(request, f"Decision saved: {recommendation.destination.city} it is!")
        return redirect("trips:detail", pk=trip.pk)

    if not trip.is_planning:
        messages.error(request, "Only a trip that is still being planned can be decided.")
        return redirect("trips:detail", pk=trip.pk)

    city = recommendation.destination.city
    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": f"Choose {city} for {trip.name}?",
        "consequences": [
            f"{city} becomes the group's destination, with a {recommendation.score:.0f}% Group Match.",
            "The trip becomes Decided and is locked: no more joining, preference changes or new recommendations.",
            "All members will see the decision in the Trip Room.",
        ],
        "confirm_label": f"Choose {city}",
        "confirm_style": "primary",
        "back_label": "Not yet",
        "back_url": reverse("trips:recommendation_detail", args=[trip.pk, destination_id]),
    })


@login_required
def member_remove(request, pk, member_id):
    trip = get_organizer_trip_or_403(request.user, pk)
    # Scoped to this trip: a member id from another trip is a 404.
    member = get_object_or_404(trip.members.select_related("user"), pk=member_id)
    name = member.user.username

    if request.method == "POST":
        try:
            cleared = remove_member(trip, member)
        except TripActionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"{name} was removed from the trip.")
            if cleared:
                messages.info(request, "Recommendations were cleared because the group changed.")
        return redirect("trips:detail", pk=trip.pk)

    if not trip.is_planning or member.user_id == trip.owner_id:
        messages.error(request, "This member can't be removed.")
        return redirect("trips:detail", pk=trip.pk)

    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": f"Remove {name} from {trip.name}?",
        "consequences": [
            f"{name} will lose access to this trip.",
            "Their preferences for this trip will be deleted.",
            "Current recommendations will be cleared.",
            f"{name} can rejoin with the invite code while the trip is still being planned.",
        ],
        "confirm_label": f"Remove {name}",
        "confirm_style": "danger",
        "back_label": "Keep member",
    })
