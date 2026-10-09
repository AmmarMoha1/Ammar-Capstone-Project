from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .forms import RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("trips:my_trips")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                _("Your account was created successfully.")
            )

            return redirect("trips:my_trips")

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )
