from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from .forms import JoinTripForm, PreferenceForm, TripForm
from .models import Preference, Trip, TripMember
from .permissions import get_member_trip_or_404
from .services.trip_actions import TripActionError, create_trip, join_trip


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
            preference = form.save(commit=False)
            preference.trip_member = membership
            preference.save()
            form.save_m2m()
            messages.success(request, "Your preferences were saved.")
            return redirect("trips:detail", pk=trip.pk)
    else:
        form = PreferenceForm(instance=existing)

    return render(
        request,
        "trips/preferences.html",
        {"trip": trip, "form": form, "is_update": existing is not None},
    )
