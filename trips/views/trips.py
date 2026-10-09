"""Trips, memberships and preferences: My Trips, the Trip Room and the organizer's trip actions."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from destinations.models import Destination

from ..forms import JoinTripForm, PreferenceForm, TripForm
from ..models import Preference, Trip, TripMember
from ..permissions import get_member_trip_or_404, get_organizer_trip_or_403
from ..services.dates import date_plan
from ..services.summary import MIN_SUBMISSIONS_FOR_BUDGETS, group_summary
from ..services.trip_actions import (
    TripActionError,
    cancel_trip,
    create_trip,
    join_trip,
    remove_member,
    save_preferences,
    update_trip,
)
from ..services.voting import vote_summary


STATUS_FILTERS = {
    "planning": Trip.Status.PLANNING,
    "decided": Trip.Status.DECIDED,
    "cancelled": Trip.Status.CANCELLED,
}
TRIPS_PER_PAGE = 9


def _search_filter(query):
    """Match the trip name or the chosen destination, in English or in its Arabic catalog name.

    Relationship query: selected_destination__city filters trips through the Destination model.
    Catalog cities are stored in English, so cities whose translated name contains the query
    are matched too (for searches typed on the Arabic version).
    """
    translated = [city for city in Destination.objects.values_list("city", flat=True) if query in _(city)]
    return (
        Q(name__icontains=query)
        | Q(selected_destination__city__icontains=query)
        | Q(selected_destination__city__in=translated)
    )


@login_required
def my_trips(request):
    # Relationship query: trips where the current user is a member (organizer included).
    # A subquery is used instead of filter(members__user=...) because that filter would
    # reuse the members join and make Count("members") count only the user's own row.
    my_trip_ids = TripMember.objects.filter(user=request.user).values("trip_id")
    my_trips_qs = Trip.objects.filter(pk__in=my_trip_ids)
    has_any_trips = my_trips_qs.exists()

    # Search: applied before the counts, so the tabs show how many matching trips each status has.
    query = request.GET.get("q", "").strip()[:100]
    if query:
        my_trips_qs = my_trips_qs.filter(_search_filter(query))

    # Aggregation: how many of my (matching) trips are in each status (for the filter tabs).
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
        for key, label in [("all", _("All")), ("planning", _("Planning")), ("decided", _("Decided")), ("cancelled", _("Cancelled"))]
    ]
    # Pagination: a long-time user can collect many trips; ?page= values out of range show the last page.
    page_obj = Paginator(trips, TRIPS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "trips/my_trips.html", {
        "trips": page_obj,
        "page_obj": page_obj,
        "filters": filters,
        "active_filter": active_filter,
        "query": query,
        "has_any_trips": has_any_trips,
    })


@login_required
def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            trip = create_trip(request.user, **form.cleaned_data)
            messages.success(
                request,
                _("Trip created. Share the code %(code)s with your friends.") % {"code": trip.invite_code},
            )
            return redirect("trips:detail", pk=trip.pk)
    else:
        form = TripForm()

    return render(request, "trips/trip_form.html", {"form": form})


@login_required
def trip_edit(request, pk):
    trip = get_organizer_trip_or_403(request.user, pk)
    if not trip.is_planning:
        messages.error(request, _("Only a trip that is still being planned can be edited."))
        return redirect("trips:detail", pk=trip.pk)

    if request.method == "POST":
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            trip, cleared = update_trip(form)
            messages.success(request, _("Trip details were updated."))
            if cleared:
                messages.info(request, _("Recommendations were cleared because the dates or departure city changed."))
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
            messages.success(request, _("%(trip)s was cancelled.") % {"trip": trip.name})
        return redirect("trips:detail", pk=trip.pk)

    if trip.status == Trip.Status.CANCELLED:
        messages.info(request, _("This trip is already cancelled."))
        return redirect("trips:detail", pk=trip.pk)

    consequences = [
        _("Members can still open the trip, but nothing can be changed afterwards."),
        _("No one can join, edit preferences or generate recommendations."),
        _("This can't be undone."),
    ]
    if trip.selected_destination:
        consequences.insert(0, _("The decision for %(city)s stays on record as cancelled.") % {
            "city": _(trip.selected_destination.city),
        })
    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": _("Cancel %(trip)s?") % {"trip": trip.name},
        "consequences": consequences,
        "confirm_label": _("Cancel trip"),
        "confirm_style": "danger",
        "back_label": _("Keep trip"),
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
                    messages.success(request, _("You joined %(trip)s. Next, add your preferences.") % {"trip": trip.name})
                else:
                    messages.info(request, _("You're already a member of %(trip)s.") % {"trip": trip.name})
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
            "votes": vote_summary(trip, my_membership) if trip.is_planning else None,
            "plan": date_plan(trip) if trip.is_planning else None,
        },
    )


@login_required
def preferences(request, pk):
    trip = get_member_trip_or_404(request.user, pk)
    if not trip.is_planning:
        messages.error(request, _("Preferences can only be changed while the trip is being planned."))
        return redirect("trips:detail", pk=trip.pk)

    # Always the current user's own membership: there is no way to address someone else's.
    membership = trip.members.get(user=request.user)
    existing = Preference.objects.filter(trip_member=membership).first()

    if request.method == "POST":
        form = PreferenceForm(request.POST, instance=existing)
        if form.is_valid():
            cleared = save_preferences(form, membership)
            messages.success(request, _("Your preferences were saved."))
            if cleared:
                messages.info(request, _("Recommendations were cleared because the group's preferences changed."))
            return redirect("trips:detail", pk=trip.pk)
    else:
        form = PreferenceForm(instance=existing)

    return render(
        request,
        "trips/preferences.html",
        {"trip": trip, "form": form, "is_update": existing is not None},
    )


def _decision(trip):
    """The saved recommendation for the chosen destination (for the decision card)."""
    if trip.selected_destination_id is None:
        return None
    return trip.recommendations.filter(destination_id=trip.selected_destination_id).first()


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
            messages.success(request, _("%(name)s was removed from the trip.") % {"name": name})
            if cleared:
                messages.info(request, _("Recommendations were cleared because the group changed."))
        return redirect("trips:detail", pk=trip.pk)

    if not trip.is_planning or member.user_id == trip.owner_id:
        messages.error(request, _("This member can't be removed."))
        return redirect("trips:detail", pk=trip.pk)

    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": _("Remove %(name)s from %(trip)s?") % {"name": name, "trip": trip.name},
        "consequences": [
            _("%(name)s will lose access to this trip.") % {"name": name},
            _("Their preferences for this trip will be deleted."),
            _("Current recommendations will be cleared."),
            _("%(name)s can rejoin with the invite code while the trip is still being planned.") % {"name": name},
        ],
        "confirm_label": _("Remove %(name)s") % {"name": name},
        "confirm_style": "danger",
        "back_label": _("Keep member"),
    })
