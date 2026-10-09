from django.shortcuts import render


def home(request):
    return render(request, "trips/home.html")
