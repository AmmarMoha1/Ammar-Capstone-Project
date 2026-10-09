"""Shared dates: members add free date ranges; the organizer can apply a suggested window."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from ..forms import AvailabilityForm
from ..models import Availability
from ..permissions import get_member_trip_or_404, get_organizer_trip_or_403
from ..services.dates import add_availability, apply_dates, date_plan
from ..services.trip_actions import TripActionError


@login_required
def dates(request, pk):
    trip = get_member_trip_or_404(request.user, pk)
    membership = trip.members.get(user=request.user)

    form = AvailabilityForm()
    if request.method == "POST":
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            try:
                add_availability(form, membership)
            except TripActionError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, _("Your free dates were added."))
                return redirect("trips:dates", pk=trip.pk)

    # Annotation: how many ranges each member has shared (only whether they shared is shown).
    members = trip.members.select_related("user").annotate(range_count=Count("availabilities"))
    return render(request, "trips/dates.html", {
        "trip": trip,
        "is_organizer": trip.is_organizer(request.user),
        "form": form,
        "my_ranges": membership.availabilities.all(),
        "max_ranges": Availability.MAX_PER_MEMBER,
        "members": members,
        "plan": date_plan(trip),
    })


@login_required
def availability_delete(request, pk, availability_id):
    trip = get_member_trip_or_404(request.user, pk)
    # Scoped to the current user's own ranges in this trip: anyone else's is a 404.
    availability = get_object_or_404(
        Availability, pk=availability_id, trip_member__trip=trip, trip_member__user=request.user
    )
    if request.method == "POST":
        if trip.is_planning:
            availability.delete()
            messages.success(request, _("The date range was removed."))
        else:
            messages.error(request, _("Dates can only be shared while the trip is being planned."))
    return redirect("trips:dates", pk=trip.pk)


@login_required
def dates_apply(request, pk, start):
    trip = get_organizer_trip_or_403(request.user, pk)
    try:
        new_start = date.fromisoformat(start)
    except ValueError:
        raise Http404("Invalid date")

    if request.method == "POST":
        try:
            trip, cleared = apply_dates(trip, new_start)
        except TripActionError as error:
            messages.error(request, str(error))
            return redirect("trips:dates", pk=trip.pk)
        messages.success(request, _("The trip dates were updated."))
        if cleared:
            messages.info(request, _("Recommendations were cleared because the dates or departure city changed."))
        return redirect("trips:detail", pk=trip.pk)

    if not trip.is_planning:
        messages.error(request, _("Only a trip that is still being planned can change its dates."))
        return redirect("trips:detail", pk=trip.pk)

    new_end = date.fromordinal(new_start.toordinal() + trip.nights)
    period = _("%(start)s – %(end)s") % {
        "start": date_format(new_start, "j M"), "end": date_format(new_end, "j M Y"),
    }
    consequences = [
        _("The trip will run %(period)s, keeping its %(nights)s nights.") % {"period": period, "nights": trip.nights},
        _("Costs and weather depend on the dates, so current recommendations and votes will be cleared."),
        _("The organizer can generate new recommendations once everyone is ready."),
    ]
    return render(request, "trips/confirm.html", {
        "trip": trip,
        "heading": _("Move %(trip)s to %(period)s?") % {"trip": trip.name, "period": period},
        "consequences": consequences,
        "confirm_label": _("Use these dates"),
        "confirm_style": "primary",
        "back_label": _("Not yet"),
        "back_url": reverse("trips:dates", args=[trip.pk]),
    })
