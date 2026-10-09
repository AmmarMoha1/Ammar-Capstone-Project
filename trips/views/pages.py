"""Public pages: the landing page and photo/font credits."""

from django.shortcuts import redirect, render

from destinations.photos import all_photos


def credits(request):
    return render(request, "credits.html", {"photos": all_photos()})


# Example postcards on the landing page: (city, photo slug, Group Match, flight hours, SAR per person).
EXAMPLE_CARDS = [
    ("Tbilisi", "tbilisi", 83, "3.5", "3,200"),
    ("Sarajevo", "sarajevo", 77, "5", "3,800"),
    ("Cairo", "cairo", 74, "2.5", "2,500"),
    ("Baku", "baku", 71, "3.5", "3,300"),
    ("Trabzon", "trabzon", 68, "4", "3,500"),
]


def home(request):
    if request.user.is_authenticated:
        return redirect("trips:my_trips")
    return render(request, "trips/home.html", {
        "example_cards": EXAMPLE_CARDS,
        "marquee_cities": [photo["city"] for photo in all_photos()],
    })
